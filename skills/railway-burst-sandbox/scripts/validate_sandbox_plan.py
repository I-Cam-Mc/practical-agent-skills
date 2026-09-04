#!/usr/bin/env python3
"""Validate an offline Railway Sandbox lifecycle plan without granting approval."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


OFFICIAL_HOST = "docs.railway.com"
REQUIRED_DOC_PATHS = ("/sandboxes", "/cli/sandbox", "/pricing")
SENSITIVE_KEY_PARTS = ("token", "password", "secret", "api_key", "apikey")


def nested(data: dict[str, Any], path: str, errors: list[str]) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            errors.append(f"missing field: {path}")
            return None
        value = value[part]
    return value


def find_sensitive_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                found.append(current)
            found.extend(find_sensitive_keys(item, current))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_sensitive_keys(item, f"{prefix}[{index}]"))
    return found


def validate(data: Any, max_doc_age_days: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["plan root must be a JSON object"], warnings

    for key in find_sensitive_keys(data):
        errors.append(f"sensitive field is not allowed in a plan: {key}")

    required_strings = (
        "purpose",
        "target.project",
        "target.environment",
        "lifecycle.success_condition",
        "lifecycle.stop_condition",
        "cost_control.currency",
        "cost_control.estimate_basis",
        "approval.scope",
    )
    for path in required_strings:
        value = nested(data, path, errors)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"field must be a non-empty string: {path}")

    checked_at = nested(data, "docs.checked_at", errors)
    if checked_at is not None:
        try:
            checked_date = date.fromisoformat(checked_at)
            age = (date.today() - checked_date).days
            if age < -1:
                errors.append("docs.checked_at cannot be in the future")
            elif age == -1:
                warnings.append(
                    "docs.checked_at is one calendar day ahead; verify the documentation timezone"
                )
            elif age > max_doc_age_days:
                warnings.append(
                    f"official documentation was checked {age} days ago; verify it again"
                )
        except (TypeError, ValueError):
            errors.append("docs.checked_at must be an ISO date")

    urls = nested(data, "docs.urls", errors)
    if urls is not None:
        if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
            errors.append("docs.urls must be a list of URLs")
        else:
            parsed = [urlparse(url) for url in urls]
            if any(item.scheme != "https" or item.netloc != OFFICIAL_HOST for item in parsed):
                errors.append("docs.urls may contain only HTTPS Railway documentation URLs")
            paths = {item.path.rstrip("/") or "/" for item in parsed}
            for required in REQUIRED_DOC_PATHS:
                if required not in paths:
                    errors.append(f"docs.urls is missing current official source: {required}")

    idle_timeout = nested(data, "lifecycle.idle_timeout_minutes", errors)
    if idle_timeout is not None:
        if isinstance(idle_timeout, bool) or not isinstance(idle_timeout, int) or idle_timeout <= 0:
            errors.append("lifecycle.idle_timeout_minutes must be a positive integer")
        elif idle_timeout > 60:
            warnings.append("idle timeout exceeds 60 minutes; justify the longer cost exposure")

    for path in ("lifecycle.explicit_destroy", "lifecycle.verify_absent_after_destroy"):
        value = nested(data, path, errors)
        if value is not None and value is not True:
            errors.append(f"field must be true: {path}")

    mode = nested(data, "network.mode", errors)
    if mode is not None and mode not in {"isolated", "private", "default"}:
        errors.append("network.mode must be isolated, private or default")
    justification = nested(data, "network.justification", errors)
    if mode in {"private", "default"} and (
        not isinstance(justification, str) or not justification.strip()
    ):
        errors.append("broader network access requires network.justification")

    amount = nested(data, "cost_control.maximum_estimated_amount", errors)
    if amount is not None and (
        isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0
    ):
        errors.append("cost_control.maximum_estimated_amount must be a positive number")

    for path in ("approval.create", "approval.destroy"):
        value = nested(data, path, errors)
        if value is not None and value not in {"pending", "approved"}:
            errors.append(f"{path} must be pending or approved")

    warnings.append("an approved field records intent but does not prove user authorisation")
    return errors, warnings


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("plan", type=Path, help="JSON plan to validate")
    result.add_argument(
        "--max-doc-age-days",
        type=int,
        default=7,
        help="warn when official docs were checked longer ago (default: 7)",
    )
    result.add_argument("--json", action="store_true", help="emit machine-readable output")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.max_doc_age_days < 0:
        print("ERROR: --max-doc-age-days cannot be negative", file=sys.stderr)
        return 2
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read plan: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate(data, args.max_doc_age_days)
    report = {"status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: Railway Sandbox plan")
        for error in errors:
            print(f"  FAIL: {error}")
        for warning in warnings:
            print(f"  NOTE: {warning}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
