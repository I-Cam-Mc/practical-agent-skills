from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "measure_charging.py"
SPEC = importlib.util.spec_from_file_location("measure_charging", MODULE_PATH)
assert SPEC and SPEC.loader
measure_charging = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = measure_charging
SPEC.loader.exec_module(measure_charging)


CHARGING_FIXTURE = r'''
+-o AppleSmartBattery  <class AppleSmartBattery>
  {
    "AdapterDetails" = {"Watts"=94,"Name"="Example 96W USB-C Adapter"}
    "SystemPowerIn" = 86445
    "SystemVoltageIn" = 20000
    "SystemCurrentIn" = 4322
    "Voltage" = 11404
    "InstantAmperage" = 4297
    "UnrelatedPrivateField" = "SENSITIVE-FIXTURE-VALUE"
  }
'''


class ParseIoregTests(unittest.TestCase):
    def test_calculates_system_and_battery_power(self) -> None:
        sample = measure_charging.parse_ioreg(CHARGING_FIXTURE)
        self.assertAlmostEqual(sample.system_input_w, 86.445)
        self.assertAlmostEqual(sample.battery_power_w, 49.002988)
        self.assertEqual(sample.adapter_capacity_w, 94.0)
        self.assertEqual(sample.state, "charging")

    def test_decodes_unsigned_discharge_current(self) -> None:
        unsigned_minus_1000 = (1 << 64) - 1000
        fixture = f'''{{
          "Voltage" = 12000
          "InstantAmperage" = {unsigned_minus_1000}
        }}'''
        sample = measure_charging.parse_ioreg(fixture)
        self.assertEqual(sample.battery_current_a, -1.0)
        self.assertEqual(sample.battery_power_w, -12.0)
        self.assertEqual(sample.state, "discharging")

    def test_summary_excludes_raw_and_identifying_fields(self) -> None:
        sample = measure_charging.parse_ioreg(CHARGING_FIXTURE)
        summary = measure_charging.summarise([sample, sample])
        rendered = measure_charging.format_human(summary)
        self.assertNotIn("UnrelatedPrivateField", rendered)
        self.assertNotIn("SENSITIVE-FIXTURE-VALUE", rendered)
        self.assertAlmostEqual(summary["derived_system_and_conversion_w"], 37.442)

    def test_fails_when_supported_fields_are_absent(self) -> None:
        with self.assertRaises(measure_charging.MeasurementError):
            measure_charging.parse_ioreg('{"UnrelatedPrivateField"="private"}')


if __name__ == "__main__":
    unittest.main()
