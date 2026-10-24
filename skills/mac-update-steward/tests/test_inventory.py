"""Behavioural tests use synthetic bundles and executable fixtures only."""

import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inventory.py"


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apps = self.root / "Applications"
        self.apps.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.output = self.root / "inventory.json"

    def bundle(self, relative, receipt=False):
        bundle = self.apps / relative
        contents = bundle / "Contents"
        contents.mkdir(parents=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": "org.example.fixture",
            "CFBundleShortVersionString": "1.2.3",
            "CFBundleVersion": "123",
        }))
        if receipt:
            receipt_path = contents / "_MASReceipt" / "receipt"
            receipt_path.parent.mkdir()
            receipt_path.write_bytes(b"synthetic receipt")
        return bundle

    def run_inventory(self, *args):
        env = dict(os.environ, PATH=str(self.bin))
        return subprocess.run([
            sys.executable, str(SCRIPT), "--output", str(self.output),
            "--app-root", str(self.apps), "--runtime", "git", *args,
        ], env=env, capture_output=True, text=True, timeout=10)

    def executable(self, name, code):
        path = self.bin / name
        path.write_text("#!" + sys.executable + "\n" + code)
        path.chmod(0o700)
        return path

    def test_reports_actual_bundle_versions_and_receipt_as_evidence_only(self):
        app = self.bundle("Example.app", receipt=True)
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["applications"], [{
            "path": str(app), "bundle_id": "org.example.fixture",
            "version": "1.2.3", "build": "123", "app_store_receipt": True,
        }])
        self.assertTrue(report["captured_at"].endswith("Z"))
        self.assertTrue(any("receipt" in gap.lower() for gap in report["gaps"]))

    def test_discovery_excludes_nested_bundles_backups_staged_and_symlinks(self):
        visible = self.bundle("Vendor/Useful.app")
        self.bundle("Vendor/Deeper/Hidden.app")
        self.bundle("Backups/Old.app")
        self.bundle("staged/Preview.app")
        self.bundle("old/Previous.app")
        self.bundle("Main.app/Contents/Helpers/Helper.app")
        main = self.apps / "Main.app"
        (main / "Contents" / "Info.plist").write_bytes(plistlib.dumps({}))
        (self.apps / "Alias.app").symlink_to(visible, target_is_directory=True)
        (self.apps / "LinkedVendor").symlink_to(visible.parent, target_is_directory=True)
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual({app["path"] for app in report["applications"]}, {str(visible), str(main)})

    def test_named_backup_staged_and_hidden_app_copies_are_excluded(self):
        current = self.bundle("Editor.app")
        self.bundle("Editor Backup.app")
        self.bundle(".Hidden.app")
        self.bundle("Vendor/Editor-staged.app")
        self.bundle("Vendor/Editor-old.app")
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual([app["path"] for app in report["applications"]], [str(current)])

    def test_invalid_bundle_does_not_hide_other_apps_and_records_coverage_gap(self):
        valid = self.bundle("Good.app")
        invalid = self.bundle("Bad.app")
        (invalid / "Contents" / "Info.plist").write_bytes(b"invalid plist")
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual([app["path"] for app in report["applications"]], [str(valid)])
        self.assertTrue(any("Bad.app" in gap for gap in report["gaps"]))

    def test_inventory_is_private_and_existing_output_is_never_overwritten(self):
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.output.write_text("preserve me")
        second = self.run_inventory()
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(self.output.read_text(), "preserve me")

    def test_runtime_reports_resolved_and_real_binary_with_actual_version(self):
        target = self.executable("fixture", "import sys\nassert sys.argv[1:] == ['--version']\nprint('git version 2.0.fixture')\n")
        alias = self.bin / "git"
        alias.symlink_to(target)
        result = self.run_inventory("--runtime", "uv")
        self.assertEqual(result.returncode, 0, result.stderr)
        runtimes = json.loads(self.output.read_text())["runtimes"]
        self.assertEqual(runtimes[0]["name"], "git")
        self.assertEqual(runtimes[0]["state"], "ok")
        self.assertEqual(runtimes[0]["resolved_path"], str(alias))
        self.assertEqual(runtimes[0]["real_path"], str(target.resolve()))
        self.assertEqual(runtimes[0]["version_output"], "git version 2.0.fixture")
        self.assertEqual(runtimes[1]["state"], "unavailable")

    def test_invalid_timeout_is_rejected_before_creating_output(self):
        for timeout in ("0", "-1", "nan", "inf"):
            with self.subTest(timeout=timeout):
                result = self.run_inventory("--timeout", timeout)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    def test_timeout_stops_owned_child_group_but_preserves_unrelated_process(self):
        owned_marker = self.root / "owned-completed"
        unrelated_marker = self.root / "unrelated-completed"
        child_code = "import time,pathlib;time.sleep(0.7);pathlib.Path({!r}).write_text('ran')".format(str(owned_marker))
        self.executable("git", "import subprocess,sys\nsubprocess.Popen([sys.executable, '-c', {!r}])\nprint('started')\n".format(child_code))
        unrelated = subprocess.Popen([sys.executable, "-c", "import time,pathlib;time.sleep(0.5);pathlib.Path({!r}).write_text('ran')".format(str(unrelated_marker))])
        self.addCleanup(lambda: unrelated.wait(timeout=3))
        result = self.run_inventory("--timeout", "0.3")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["runtimes"][0]["state"], "timeout")
        time.sleep(0.8)
        self.assertFalse(owned_marker.exists())
        self.assertTrue(unrelated_marker.exists())

    def test_output_flood_is_bounded_and_marked_incomplete(self):
        self.executable("git", "import os\nwhile True: os.write(1, b'v' * 8192)\n")
        result = self.run_inventory("--timeout", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        runtime = json.loads(self.output.read_text())["runtimes"][0]
        self.assertEqual(runtime["state"], "output_limit")
        self.assertLessEqual(len(runtime["version_output"].encode()), 65536)

    def test_arbitrary_runtime_name_and_updater_runner_names_are_rejected(self):
        for name in ("evil", "brew", "codex", "orca", "tailscale", "/usr/bin/git"):
            with self.subTest(name=name):
                result = self.run_inventory("--runtime", name)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())

    @unittest.skipUnless(sys.platform == "darwin", "sw_vers exists only on macOS")
    def test_macos_version_is_read_from_apple_system_tool(self):
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        platform_result = json.loads(self.output.read_text())["platform"]
        self.assertEqual(platform_result["system"], "Darwin")
        self.assertEqual(platform_result["sw_vers"]["state"], "ok")
        self.assertIn("ProductVersion:", platform_result["sw_vers"]["version_output"])
        self.assertIn("BuildVersion:", platform_result["sw_vers"]["version_output"])

    def test_malformed_xml_metadata_is_a_coverage_gap_not_a_crash(self):
        broken = self.bundle("Broken.app")
        (broken / "Contents" / "Info.plist").write_bytes(b'<?xml version="1.0"?><plist><dict>')
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["applications"], [])
        self.assertTrue(any("Broken.app" in gap for gap in report["gaps"]))

    def test_bundle_with_symlink_metadata_is_not_followed(self):
        bundle = self.bundle("Link.app")
        metadata = bundle / "Contents" / "Info.plist"
        original = self.root / "elsewhere.plist"
        metadata.rename(original)
        metadata.symlink_to(original)
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["applications"], [])
        self.assertTrue(any("Link.app" in gap for gap in report["gaps"]))

    def test_explicit_root_is_authoritative_even_if_named_old(self):
        selected = self.bundle("Old/Selected.app")
        result = self.run_inventory("--app-root", str(selected.parent))
        self.assertEqual(result.returncode, 0, result.stderr)
        apps = json.loads(self.output.read_text())["applications"]
        self.assertEqual([app["path"] for app in apps], [str(selected)])

    def test_direct_explicit_app_root_preserves_intentional_copy_observation(self):
        selected = self.bundle("Editor Backup.app")
        result = self.run_inventory("--app-root", str(selected))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual([app["path"] for app in report["applications"]], [str(selected)])
        self.assertTrue(any("not proof of active installation" in gap for gap in report["gaps"]))

    def test_direct_explicit_app_symlink_is_skipped_with_coverage_gap(self):
        original = self.bundle("Example.app")
        target = self.root / "Outside.app"
        original.rename(target)
        original.symlink_to(target, target_is_directory=True)
        result = self.run_inventory("--app-root", str(original))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["applications"], [])
        self.assertTrue(any("symlink application root" in gap for gap in report["gaps"]))

    def test_nonzero_runtime_exit_is_unavailable_not_version_success(self):
        self.executable("git", "import sys\nprint('partial output')\nsys.exit(7)\n")
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        runtime = json.loads(self.output.read_text())["runtimes"][0]
        self.assertEqual(runtime["state"], "unavailable")
        self.assertEqual(runtime["exit_code"], 7)

    def test_symlink_output_never_overwrites_target(self):
        target = self.root / "private.txt"
        target.write_text("preserve")
        self.output.symlink_to(target)
        result = self.run_inventory()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(), "preserve")

    def test_nonregular_metadata_is_a_gap_without_waiting_for_a_writer(self):
        bundle = self.bundle("Pipe.app")
        metadata = bundle / "Contents" / "Info.plist"
        metadata.unlink()
        os.mkfifo(metadata)
        result = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.output.read_text())
        self.assertEqual(report["applications"], [])
        self.assertTrue(any("Pipe.app" in gap for gap in report["gaps"]))


if __name__ == "__main__":
    unittest.main()
