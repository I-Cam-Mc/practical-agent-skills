from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_container_delivery.py"
DIGEST = "a" * 64


def write_package(root: Path, *, pinned: bool = True, user: str = "65532:65532") -> None:
    image = f"alpine@sha256:{DIGEST}" if pinned else "alpine:latest"
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "Dockerfile").write_text(
        f"FROM {image}\nCOPY . /app\nUSER {user}\n", encoding="utf-8"
    )


def run_preflight(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(target), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class VerifyContainerDeliveryTests(unittest.TestCase):
    def test_basic_profile_accepts_pinned_non_root_package(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root)
            result = run_preflight(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_unpinned_base_fails(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root, pinned=False)
            result = run_preflight(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not digest-pinned", result.stdout)

    def test_digest_pinned_arg_default_passes_with_override_warning(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
            (root / "Dockerfile").write_text(
                f"ARG BASE=alpine@sha256:{DIGEST}\nFROM ${{BASE}}\nUSER 65532\n",
                encoding="utf-8",
            )
            result = run_preflight(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("did not override", result.stdout)

    def test_root_final_user_fails(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root, user="root")
            result = run_preflight(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("final USER", result.stdout)

    def test_isolated_profile_requires_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root)
            result = run_preflight(root, "--profile", "isolated")
        self.assertEqual(result.returncode, 1)
        self.assertIn("network isolation", result.stdout)

    def test_isolated_profile_accepts_required_flags(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root)
            (root / "run.sh").write_text(
                "#!/bin/sh\n"
                "docker run --network=none --read-only --cap-drop=ALL "
                "--security-opt=no-new-privileges --pids-limit=32 "
                "--memory=256m --cpus=1 fixture\n",
                encoding="utf-8",
            )
            result = run_preflight(root, "--profile", "isolated")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_docker_socket_access_fails(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root)
            (root / "run.sh").write_text(
                "docker run -v /var/run/docker.sock:/var/run/docker.sock fixture\n",
                encoding="utf-8",
            )
            result = run_preflight(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Docker socket", result.stdout)

    def test_negative_assertion_in_test_directory_does_not_fail_runtime_scan(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_package(root)
            tests = root / "tests"
            tests.mkdir()
            (tests / "runtime.sh").write_text(
                "test ! -e /var/run/docker.sock\n", encoding="utf-8"
            )
            result = run_preflight(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_archive_parent_traversal_is_rejected_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            archive = Path(name) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../escaped", "nope")
            result = run_preflight(archive)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe archive member", result.stderr)

    def test_clean_zip_archive_is_inspected(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            package = root / "package"
            package.mkdir()
            write_package(package)
            archive = root / "package.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                for path in package.iterdir():
                    handle.write(path, Path("package") / path.name)
            result = run_preflight(archive)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_tar_link_is_rejected_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source.txt"
            source.write_text("fixture", encoding="utf-8")
            archive = root / "bad.tar"
            with tarfile.open(archive, "w") as handle:
                info = tarfile.TarInfo("package/link")
                info.type = tarfile.SYMTYPE
                info.linkname = "../../outside"
                handle.addfile(info)
            result = run_preflight(archive)
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-file archive member", result.stderr)


if __name__ == "__main__":
    unittest.main()
