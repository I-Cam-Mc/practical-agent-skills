from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


REFERENCE = Path(__file__).parents[1] / "references" / "mutation-manifest.md"


class ManifestDocumentationTests(unittest.TestCase):
    def test_example_defines_update_delete_and_merge(self) -> None:
        match = re.search(
            r"```json\n(.*?)\n```",
            REFERENCE.read_text(encoding="utf-8"),
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        manifest = json.loads(match.group(1))
        by_action = {item["action"]: item for item in manifest["operations"]}
        self.assertEqual(set(by_action), {"update", "delete", "merge"})

        deletion = by_action["delete"]
        self.assertIsInstance(deletion["before"], dict)
        self.assertIsNone(deletion["after"])
        self.assertEqual(deletion["tombstone"]["expected_state"], "absent")

        merge = by_action["merge"]
        self.assertTrue(merge["survivor_id"])
        self.assertTrue(merge["source_ids"])
        self.assertTrue(merge["tombstones"])


if __name__ == "__main__":
    unittest.main()
