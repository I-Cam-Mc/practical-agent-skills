#!/usr/bin/env python3
"""Portable static preflight for a Docker deliverable directory or archive."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile


MAX_MEMBERS = 10_000
MAX_UNPACKED_BYTES = 128 * 1024 * 1024
TEXT_SUFFIXES = {".sh", ".yaml", ".yml", ".json", ".toml"}
FORBIDDEN_RUNTIME_MARKERS = {
    "--privileged": "privileged container execution",
    "/var/run/docker.sock": "Docker socket access",
    "--network=host": "host network access",
    "--network host": "host network access",
    "--pid=host": "host PID namespace access",
    "--ipc=host": "host IPC namespace access",
    "--cap-add": "added Linux capabilities",
}
ISOLATED_MARKERS = {
    "network isolation": ("--network=none", "--network none"),
    "read-only root filesystem": ("--read-only",),
    "capability drop": ("--cap-drop=all", "--cap-drop all"),
    "no-new-privileges": (
        "--security-opt=no-new-privileges",
        "--security-opt no-new-privileges",
    ),
    "process limit": ("--pids-limit",),
    "memory limit": ("--memory",),
    "CPU limit": ("--cpus",),
}


class UnsafeInputError(ValueError):
    """Raised when an archive cannot be inspected safely."""


def safe_member_name(name: str) -> PurePosixPath:
    normalised = name.replace("\\", "/")
    if "\x00" in normalised or re.match(r"^[A-Za-z]:", normalised):
        raise UnsafeInputError(f"unsafe archive member: {name!r}")
    path = PurePosixPath(normalised)
    if path.is_absolute() or ".." in path.parts:
        raise UnsafeInputError(f"unsafe archive member: {name!r}")
    return path


def validate_size(member_count: int, total_bytes: int) -> None:
    if member_count > MAX_MEMBERS:
        raise UnsafeInputError(f"archive has more than {MAX_MEMBERS} members")
    if total_bytes > MAX_UNPACKED_BYTES:
        raise UnsafeInputError(
            f"archive expands beyond {MAX_UNPACKED_BYTES // (1024 * 1024)} MiB"
        )


def unpack_zip(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        validate_size(len(infos), sum(item.file_size for item in infos))
        for item in infos:
            safe_member_name(item.filename)
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UnsafeInputError(f"archive link is not allowed: {item.filename!r}")
        archive.extractall(destination)


def unpack_tar(source: Path, destination: Path) -> None:
    with tarfile.open(source, mode="r:*") as archive:
        members = archive.getmembers()
        validate_size(len(members), sum(item.size for item in members))
        for item in members:
            safe_member_name(item.name)
            if not (item.isfile() or item.isdir()):
                raise UnsafeInputError(
                    f"non-file archive member is not allowed: {item.name!r}"
                )
        archive.extractall(destination)


def package_root(extracted: Path) -> Path:
    visible = [item for item in extracted.iterdir() if item.name != "__MACOSX"]
    if len(visible) == 1 and visible[0].is_dir():
        return visible[0]
    return extracted


def dockerfiles(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("Dockerfile*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    )


def base_image(line: str) -> str | None:
    tokens = line.split()
    if not tokens or tokens[0].upper() != "FROM":
        return None
    index = 1
    while index < len(tokens) and tokens[index].startswith("--"):
        index += 1
    return tokens[index] if index < len(tokens) else None


def inspect_dockerfile(path: Path, errors: list[str], warnings: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read {path.name}: {exc}")
        return

    arg_defaults: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = re.match(r"^\s*ARG\s+([A-Za-z_][A-Za-z0-9_]*)=(\S+)\s*$", raw_line)
        if match:
            arg_defaults[match.group(1)] = match.group(2)

    bases = [image for line in text.splitlines() if (image := base_image(line))]
    if not bases:
        errors.append(f"{path.name} has no readable FROM instruction")
    for image in bases:
        resolved_image = image
        variable = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", image)
        if variable:
            variable_name = variable.group(1) or variable.group(2)
            resolved_image = arg_defaults.get(variable_name, "")
            if resolved_image:
                warnings.append(
                    f"{path.name} FROM uses digest-pinned ARG {variable_name}; verify the release build did not override it"
                )
            else:
                errors.append(
                    f"{path.name} FROM variable has no verifiable default: {image}"
                )
                continue
        if resolved_image.lower() == "scratch":
            continue
        if not re.search(r"@sha256:[0-9a-fA-F]{64}$", resolved_image):
            errors.append(f"{path.name} base image is not digest-pinned: {image}")

    users = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.upper().startswith("USER "):
            users.append(line[5:].strip())
    if not users:
        errors.append(f"{path.name} does not declare a final USER")
    else:
        final_user = users[-1].split(":", 1)[0].strip().lower()
        if final_user in {"", "0", "root"} or "$" in final_user:
            errors.append(f"{path.name} final USER is root or cannot be verified")


def runtime_text(root: Path) -> str:
    chunks: list[str] = []
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        lowered_parts = {part.lower() for part in relative_parts}
        if not path.is_file() or ".git" in relative_parts:
            continue
        if lowered_parts & {"test", "tests", "spec", "specs", "fixtures"}:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and "compose" not in path.name.lower():
            continue
        try:
            if path.stat().st_size <= 2 * 1024 * 1024:
                chunks.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
    return "\n".join(chunks)


def check_shell_syntax(root: Path, errors: list[str]) -> None:
    shell = shutil.which("sh")
    if shell is None:
        return
    for path in sorted(root.rglob("*.sh")):
        if ".git" in path.relative_to(root).parts:
            continue
        result = subprocess.run(
            [shell, "-n", os.fspath(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "shell parser rejected the file"
            errors.append(f"invalid shell syntax in {path.relative_to(root)}: {detail}")


def inspect(root: Path, profile: str) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    if not any((root / name).is_file() for name in ("README.md", "README", "README.txt")):
        errors.append("package has no README")

    found_dockerfiles = dockerfiles(root)
    if not found_dockerfiles:
        errors.append("package has no Dockerfile")
    for path in found_dockerfiles:
        inspect_dockerfile(path, errors, warnings)

    combined_runtime = runtime_text(root)
    normalised_runtime = combined_runtime.lower()
    for marker, meaning in FORBIDDEN_RUNTIME_MARKERS.items():
        if marker.lower() in normalised_runtime:
            errors.append(f"runtime configuration contains {meaning}: {marker}")

    if profile == "isolated":
        for meaning, alternatives in ISOLATED_MARKERS.items():
            if not any(marker.lower() in normalised_runtime for marker in alternatives):
                errors.append(
                    f"isolated profile lacks {meaning}: expected one of {', '.join(alternatives)}"
                )

    check_shell_syntax(root, errors)
    warnings.append(
        "static inspection only; build, runtime, SBOM, provenance and vulnerability claims remain unverified"
    )
    return {
        "status": "PASS" if not errors else "FAIL",
        "profile": profile,
        "root": os.fspath(root),
        "errors": errors,
        "warnings": warnings,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("target", type=Path, help="package directory, .zip, .tar or compressed tar")
    result.add_argument(
        "--profile",
        choices=("basic", "isolated"),
        default="basic",
        help="isolated additionally requires hardened offline runtime flags",
    )
    result.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    source = args.target.expanduser().resolve()
    if not source.exists():
        print(f"ERROR: target does not exist: {source}", file=sys.stderr)
        return 2

    try:
        if source.is_dir():
            report = inspect(source, args.profile)
        else:
            with tempfile.TemporaryDirectory(prefix="container-preflight-") as temp_name:
                extracted = Path(temp_name)
                if zipfile.is_zipfile(source):
                    unpack_zip(source, extracted)
                elif tarfile.is_tarfile(source):
                    unpack_tar(source, extracted)
                else:
                    raise UnsafeInputError("target is not a supported archive")
                report = inspect(package_root(extracted), args.profile)
                report["root"] = "<temporary clean extraction>"
    except (OSError, UnsafeInputError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: static container delivery preflight ({report['profile']})")
        for error in report["errors"]:
            print(f"  FAIL: {error}")
        for warning in report["warnings"]:
            print(f"  NOTE: {warning}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
