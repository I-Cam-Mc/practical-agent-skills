from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import re
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_claim_register.py"
SPEC = importlib.util.spec_from_file_location("validate_claim_register", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REFERENCE = SCRIPT.parents[1] / "references" / "claim-register.md"


def documented_register() -> dict:
    match = re.search(
        r"```json\n(.*?)\n```",
        REFERENCE.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


def valid_register() -> dict:
    return {
        "register_version": 1,
        "claims": [
            {
                "id": "synthetic-result",
                "claim": "A synthetic system received 120 comparison-rating points",
                "benchmark": {
                    "name": "Synthetic Deliverable Evaluation",
                    "version": "v1",
                    "task_design": "Systems produce bounded deliverables from synthetic briefs",
                    "scoring_method": "Reviewers choose the stronger deliverable in blind pairs",
                    "split": "public synthetic fixture",
                },
                "result": {
                    "value": 120,
                    "metric": "comparison rating",
                    "unit": "rating points",
                    "direction": "higher",
                    "interpretation": "Relative preference under this pairing protocol",
                    "not_equivalent_to": "120 percent accuracy",
                },
                "system": {
                    "name": "Synthetic System",
                    "model_version": "fixture-v1",
                    "effort": "fixed synthetic setting",
                    "tools": ["fixture editor"],
                    "scaffolding": "documented synthetic harness",
                    "fallback_routing": "none",
                },
                "evidence": [
                    {
                        "publisher_relationship": "benchmark-owner",
                        "source_kind": "methodology",
                        "url": "https://example.org/method",
                        "published_at": "unknown",
                        "accessed_at": date.today().isoformat(),
                        "supports": "Synthetic task and scoring protocol",
                    }
                ],
                "limitations": ["Synthetic fixture, not a real model claim"],
                "status": "verified",
            }
        ],
    }


class ValidateClaimRegisterTests(unittest.TestCase):
    def test_documented_register_passes(self) -> None:
        errors, _ = MODULE.validate(documented_register(), 30)
        self.assertEqual(errors, [])

    def test_complete_register_passes(self) -> None:
        errors, warnings = MODULE.validate(valid_register(), 30)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_fallback_routing_fails(self) -> None:
        register = valid_register()
        del register["claims"][0]["system"]["fallback_routing"]
        errors, _ = MODULE.validate(register, 30)
        self.assertTrue(any("fallback_routing" in error for error in errors))

    def test_vendor_only_evidence_is_flagged(self) -> None:
        register = valid_register()
        register["claims"][0]["evidence"][0]["publisher_relationship"] = "vendor"
        errors, warnings = MODULE.validate(register, 30)
        self.assertEqual(errors, [])
        self.assertTrue(any("vendor-only" in warning for warning in warnings))

    def test_stale_source_is_flagged(self) -> None:
        register = valid_register()
        register["claims"][0]["evidence"][0]["accessed_at"] = (
            date.today() - timedelta(days=31)
        ).isoformat()
        errors, warnings = MODULE.validate(register, 30)
        self.assertEqual(errors, [])
        self.assertTrue(any("31 days ago" in warning for warning in warnings))

    def test_one_day_ahead_allows_timezone_boundary(self) -> None:
        register = valid_register()
        register["claims"][0]["evidence"][0]["accessed_at"] = (
            date.today() + timedelta(days=1)
        ).isoformat()
        errors, warnings = MODULE.validate(register, 30)
        self.assertEqual(errors, [])
        self.assertTrue(any("timezone" in warning for warning in warnings))

    def test_malformed_source_url_fails(self) -> None:
        register = valid_register()
        register["claims"][0]["evidence"][0]["url"] = "search result"
        errors, _ = MODULE.validate(register, 30)
        self.assertTrue(any("direct HTTP" in error for error in errors))

    def test_duplicate_claim_id_fails(self) -> None:
        register = valid_register()
        register["claims"].append(deepcopy(register["claims"][0]))
        errors, _ = MODULE.validate(register, 30)
        self.assertTrue(any("duplicate id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
