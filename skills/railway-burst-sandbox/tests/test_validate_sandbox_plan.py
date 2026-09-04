from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path
import re
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_sandbox_plan.py"
SPEC = importlib.util.spec_from_file_location("validate_sandbox_plan", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
REFERENCE = SCRIPT.parents[1] / "references" / "live-checklist.md"


def documented_plan() -> dict:
    match = re.search(
        r"```json\n(.*?)\n```",
        REFERENCE.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


def valid_plan() -> dict:
    return {
        "purpose": "Run a bounded synthetic test and collect its report",
        "target": {"project": "example", "environment": "temporary"},
        "docs": {
            "checked_at": date.today().isoformat(),
            "urls": [
                "https://docs.railway.com/sandboxes",
                "https://docs.railway.com/cli/sandbox",
                "https://docs.railway.com/pricing",
            ],
        },
        "lifecycle": {
            "idle_timeout_minutes": 30,
            "explicit_destroy": True,
            "verify_absent_after_destroy": True,
            "success_condition": "The synthetic test report exists and parses",
            "stop_condition": "One attempt or twenty minutes",
        },
        "network": {"mode": "isolated", "justification": ""},
        "cost_control": {
            "currency": "AUD",
            "maximum_estimated_amount": 1.0,
            "estimate_basis": "Synthetic current-rate fixture for validator tests",
        },
        "approval": {
            "create": "pending",
            "destroy": "pending",
            "scope": "Create and destroy one synthetic sandbox in the named environment",
        },
    }


class ValidateSandboxPlanTests(unittest.TestCase):
    def test_documented_plan_passes(self) -> None:
        errors, _ = MODULE.validate(documented_plan(), 7)
        self.assertEqual(errors, [])

    def test_valid_plan_passes(self) -> None:
        errors, warnings = MODULE.validate(valid_plan(), 7)
        self.assertEqual(errors, [])
        self.assertTrue(any("does not prove" in warning for warning in warnings))

    def test_sensitive_field_is_rejected(self) -> None:
        plan = valid_plan()
        plan["api_token"] = "not-a-real-token"
        errors, _ = MODULE.validate(plan, 7)
        self.assertTrue(any("sensitive field" in error for error in errors))

    def test_broader_network_requires_justification(self) -> None:
        plan = valid_plan()
        plan["network"] = {"mode": "private", "justification": ""}
        errors, _ = MODULE.validate(plan, 7)
        self.assertTrue(any("network.justification" in error for error in errors))

    def test_stale_documentation_produces_warning(self) -> None:
        plan = valid_plan()
        plan["docs"]["checked_at"] = (date.today() - timedelta(days=8)).isoformat()
        errors, warnings = MODULE.validate(plan, 7)
        self.assertEqual(errors, [])
        self.assertTrue(any("8 days ago" in warning for warning in warnings))

    def test_one_day_ahead_allows_timezone_boundary(self) -> None:
        plan = valid_plan()
        plan["docs"]["checked_at"] = (date.today() + timedelta(days=1)).isoformat()
        errors, warnings = MODULE.validate(plan, 7)
        self.assertEqual(errors, [])
        self.assertTrue(any("timezone" in warning for warning in warnings))

    def test_cleanup_verification_cannot_be_disabled(self) -> None:
        plan = deepcopy(valid_plan())
        plan["lifecycle"]["verify_absent_after_destroy"] = False
        errors, _ = MODULE.validate(plan, 7)
        self.assertTrue(any("verify_absent_after_destroy" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
