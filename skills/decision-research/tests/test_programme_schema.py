from __future__ import annotations

import csv
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
REQUIRED_FINANCE_FIELDS = {
    "price_basis",
    "gross_or_net",
    "one_time_or_ongoing",
    "source_location",
}


class ProgrammeSchemaTests(unittest.TestCase):
    def test_finance_fields_exist_in_schema_and_template(self) -> None:
        schema = (ROOT / "references" / "register-schemas.md").read_text(encoding="utf-8")
        with (ROOT / "assets" / "programme-inventory-template.csv").open(
            newline="", encoding="utf-8"
        ) as source:
            header = set(next(csv.reader(source)))
        match = re.search(r"## Programme inventory\n\n`([^`]+)`", schema)
        self.assertIsNotNone(match)
        documented = set(match.group(1).split(","))

        self.assertEqual(REQUIRED_FINANCE_FIELDS - header, set())
        self.assertEqual(REQUIRED_FINANCE_FIELDS - documented, set())
        self.assertEqual(header, documented)


if __name__ == "__main__":
    unittest.main()
