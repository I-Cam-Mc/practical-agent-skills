from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "diagnose_mac.py"
SPEC = importlib.util.spec_from_file_location("diagnose_mac", MODULE_PATH)
assert SPEC and SPEC.loader
diagnose_mac = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = diagnose_mac
SPEC.loader.exec_module(diagnose_mac)


class ParserTests(unittest.TestCase):
    def test_uses_last_top_cpu_observation(self) -> None:
        fixture = """
CPU usage: 8.0% user, 7.0% sys, 85.0% idle
CPU usage: 20.0% user, 10.0% sys, 70.0% idle
"""
        parsed = diagnose_mac.parse_top_cpu(fixture)
        self.assertEqual(parsed["idle_percent"], 70.0)

    def test_parses_swap_units(self) -> None:
        parsed = diagnose_mac.parse_swapusage(
            "vm.swapusage: total = 4.00G used = 1536.00M free = 2.50G"
        )
        self.assertEqual(parsed["total_bytes"], 4 * 1024**3)
        self.assertEqual(parsed["used_bytes"], 1536 * 1024**2)

    def test_maps_pressure_levels(self) -> None:
        self.assertEqual(diagnose_mac.parse_pressure_level("1\n"), "normal")
        self.assertEqual(diagnose_mac.parse_pressure_level("2\n"), "warning")
        self.assertEqual(diagnose_mac.parse_pressure_level("4\n"), "critical")
        self.assertEqual(diagnose_mac.parse_pressure_level("99\n"), "unknown")

    def test_aggregates_processes_without_arguments_or_paths(self) -> None:
        fixture = """
 10.0 102400 /Applications/Example.app/Contents/MacOS/Example
  5.0  51200 /Applications/Example.app/Contents/MacOS/Example
  1.0  25600 /opt/tools/Worker
"""
        processes = diagnose_mac.parse_processes(fixture, 2)
        self.assertEqual(processes[0]["name"], "Example")
        self.assertEqual(processes[0]["process_count"], 2)
        self.assertEqual(processes[0]["cpu_percent"], 15.0)
        self.assertNotIn("Applications", str(processes))
        self.assertNotIn("opt/tools", str(processes))

    def test_parses_load_average_variants(self) -> None:
        self.assertEqual(
            diagnose_mac.parse_load_averages("load averages: 2.50 1.25 0.75"),
            [2.5, 1.25, 0.75],
        )
        self.assertEqual(
            diagnose_mac.parse_load_averages("load average: 0.10, 0.20, 0.30"),
            [0.1, 0.2, 0.3],
        )


if __name__ == "__main__":
    unittest.main()
