#!/usr/bin/env python3
"""Read-only local bundle and command inventory. Python 3.9+, standard library."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import plistlib
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
from xml.parsers.expat import ExpatError


DEFAULT_RUNTIMES = ("python3", "node", "npm", "uv", "git")
ALLOWED_RUNTIMES = DEFAULT_RUNTIMES + ("bun", "deno", "ruby", "rustc", "cargo", "swift")
OUTPUT_LIMIT = 64 * 1024


def bounded_command(command, timeout):
    """Bound combined output and elapsed time; terminate only our new process group."""
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    except OSError:
        return {"state": "unavailable", "version_output": "", "exit_code": None}
    output = bytearray()
    state = "ok"
    deadline = time.monotonic() + timeout
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map() or process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                state = "timeout"
                break
            if not selector.get_map():
                time.sleep(min(remaining, 0.01))
                continue
            events = selector.select(min(remaining, 0.05))
            for key, _ in events:
                block = os.read(key.fileobj.fileno(), min(8192, OUTPUT_LIMIT - len(output) + 1))
                if not block:
                    selector.unregister(key.fileobj)
                elif len(output) + len(block) > OUTPUT_LIMIT:
                    output.extend(block[:OUTPUT_LIMIT - len(output)])
                    state = "output_limit"
                    break
                else:
                    output.extend(block)
            if state != "ok":
                break
    finally:
        selector.close()
        if state != "ok" or process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.stdout.close()
        process.wait(timeout=2)
    if state == "ok" and process.returncode != 0:
        state = "unavailable"
    return {"state": state, "version_output": output.decode("utf-8", errors="replace").strip(),
            "exit_code": process.returncode}


def runtime_inventory(names, timeout):
    results = []
    for name in dict.fromkeys(names):
        resolved = shutil.which(name)
        result = {"name": name, "resolved_path": os.path.abspath(resolved) if resolved else None,
                  "real_path": os.path.realpath(resolved) if resolved else None}
        if resolved:
            result.update(bounded_command([os.path.abspath(resolved), "--version"], timeout))
        else:
            result.update(state="unavailable", version_output="", exit_code=None)
        results.append(result)
    return results


EXCLUDED_DIRECTORY = re.compile(r"(?:^|[\s._-])(backup[s]?|staged|staging|old|previous|archive[s]?|trash)(?:$|[\s._-])", re.I)


def bundles(root, gaps, depth=0):
    """Inspect roots and one vendor directory, without following symlink entries.

    Explicit roots override name exclusions, including an explicitly selected
    .app. Discovered descendants are always subject to the name filters.
    """
    if root.is_symlink() or not root.is_dir():
        gaps.append("Skipped missing, unreadable or symlink application root: " + str(root))
        return
    if root.suffix.lower() == ".app":
        yield root
        return
    try:
        entries = sorted(root.iterdir())
    except OSError:
        gaps.append("Cannot list application directory: " + str(root))
        return
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.name.startswith(".") or EXCLUDED_DIRECTORY.search(entry.name):
            continue
        if entry.suffix.lower() == ".app":
            yield entry
        elif depth < 1:
            yield from bundles(entry, gaps, depth + 1)


def inventory(roots, runtimes, timeout):
    applications = []
    gaps = []
    seen = set()
    for root in roots:
        for bundle in bundles(root.expanduser().absolute(), gaps):
            if bundle in seen:
                continue
            seen.add(bundle)
            try:
                contents = bundle / "Contents"
                metadata = contents / "Info.plist"
                if contents.is_symlink() or metadata.is_symlink() or not metadata.is_file():
                    raise ValueError("Metadata must be a regular file within the bundle")
                descriptor = os.open(metadata, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
                with os.fdopen(descriptor, "rb") as source:
                    if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                        raise ValueError("Metadata is not a regular file")
                    data = source.read(1024 * 1024 + 1)
                if len(data) > 1024 * 1024:
                    raise ValueError("Oversized Info.plist")
                info = plistlib.loads(data)
                if not isinstance(info, dict):
                    raise ValueError("Info.plist is not a dictionary")
                info = {key: value if isinstance(value, (str, int)) else None
                        for key, value in info.items()}
            except (OSError, ValueError, plistlib.InvalidFileException, OverflowError, ExpatError, RecursionError):
                gaps.append("Cannot read bounded bundle metadata: " + str(bundle))
                continue
            applications.append({
                "path": str(bundle.absolute()),
                "bundle_id": info.get("CFBundleIdentifier"),
                "version": info.get("CFBundleShortVersionString"),
                "build": info.get("CFBundleVersion"),
                "app_store_receipt": (bundle / "Contents" / "_MASReceipt" / "receipt").is_file(),
            })
    platform_result = {"system": platform.system(), "machine": platform.machine()}
    if platform_result["system"] == "Darwin":
        platform_result["sw_vers"] = bounded_command(["/usr/bin/sw_vers"], timeout)
    else:
        gaps.append("Host is not macOS; macOS system version was not queried.")
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platform": platform_result,
        "applications": applications,
        "runtimes": runtime_inventory(runtimes, timeout),
        "gaps": gaps + [
            "Bundle inventory is not a complete installed-software or update-status assessment.",
            "Discovery covers explicit roots, direct bundles and one vendor folder; discovered hidden, backup, staged and symlink directories and app copies are excluded.",
            "Explicit application roots override name filters, so explicitly selected copies are observations, not proof of active installation.",
            "App Store receipt presence is not proof of an installed update or current eligibility.",
            "On-disk runtime versions do not prove which runtime existing processes are using.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="new private JSON file; existing paths are never overwritten")
    parser.add_argument("--app-root", action="append", type=Path,
                        help="repeat to replace default roots /Applications and ~/Applications")
    parser.add_argument("--runtime", action="append", choices=ALLOWED_RUNTIMES,
                        help="repeat to replace default probes python3,node,npm,uv,git")
    parser.add_argument("--timeout", type=float, default=10,
                        help="per-command wall time in seconds, greater than 0 and at most 60 (default 10)")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60:
        parser.error("--timeout must be a finite number greater than zero and at most 60 seconds")
    try:
        descriptor = os.open(args.output.expanduser(), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
            result = inventory(args.app_root or [Path("/Applications"), Path.home() / "Applications"],
                               args.runtime or DEFAULT_RUNTIMES, args.timeout)
            json.dump(result, destination, indent=2, allow_nan=False)
            destination.write("\n")
    except OSError as error:
        print("Inventory could not be saved ({}); existing files are never overwritten.".format(type(error).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
