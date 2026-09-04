#!/usr/bin/env python3
"""Validate the completeness and provenance fields of an AI claim register."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


RELATIONSHIPS = {"vendor", "benchmark-owner", "independent", "unknown"}
SOURCE_KINDS = {"methodology", "official-result", "paper", "announcement", "analysis"}
STATUSES = {"verified", "provisional", "conflicted", "unverified"}
DIRECTIONS = {"higher", "lower"}


def field(data: dict[str, Any], path: str, errors: list[str], claim_id: str) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            errors.append(f"{claim_id}: missing field {path}")
            return None
        value = value[part]
    return value


def require_text(data: dict[str, Any], path: str, errors: list[str], claim_id: str) -> Any:
    value = field(data, path, errors, claim_id)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        errors.append(f"{claim_id}: {path} must be a non-empty string")
    return value


def validate_evidence(
    items: Any,
    claim_id: str,
    max_source_age_days: int,
    errors: list[str],
    warnings: list[str],
) -> set[str]:
    relationships: set[str] = set()
    if not isinstance(items, list) or not items:
        errors.append(f"{claim_id}: evidence must be a non-empty list")
        return relationships

    for index, item in enumerate(items):
        prefix = f"{claim_id}: evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        relationship = item.get("publisher_relationship")
        if relationship not in RELATIONSHIPS:
            errors.append(f"{prefix}.publisher_relationship is invalid")
        else:
            relationships.add(relationship)

        if item.get("source_kind") not in SOURCE_KINDS:
            errors.append(f"{prefix}.source_kind is invalid")

        url = item.get("url")
        if not isinstance(url, str):
            errors.append(f"{prefix}.url must be a direct HTTP or HTTPS URL")
        else:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{prefix}.url must be a direct HTTP or HTTPS URL")

        supports = item.get("supports")
        if not isinstance(supports, str) or not supports.strip():
            errors.append(f"{prefix}.supports must explain the source's role")

        accessed_at = item.get("accessed_at")
        try:
            accessed = date.fromisoformat(accessed_at)
            age = (date.today() - accessed).days
            if age < 0:
                errors.append(f"{prefix}.accessed_at cannot be in the future")
            elif age > max_source_age_days:
                warnings.append(
                    f"{prefix} was accessed {age} days ago; refresh time-sensitive claims"
                )
        except (TypeError, ValueError):
            errors.append(f"{prefix}.accessed_at must be an ISO date")

    return relationships


def validate(data: Any, max_source_age_days: int) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["register root must be a JSON object"], warnings
    if data.get("register_version") != 1:
        errors.append("register_version must be 1")

    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("claims must be a non-empty list")
        return errors, warnings

    seen_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claim[{index}] must be an object")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            claim_id = f"claim[{index}]"
            errors.append(f"{claim_id}: id must be a non-empty string")
        elif claim_id in seen_ids:
            errors.append(f"{claim_id}: duplicate id")
        seen_ids.add(claim_id)

        for path in (
            "claim",
            "benchmark.name",
            "benchmark.version",
            "benchmark.task_design",
            "benchmark.scoring_method",
            "benchmark.split",
            "result.metric",
            "result.unit",
            "result.interpretation",
            "result.not_equivalent_to",
            "system.name",
            "system.model_version",
            "system.effort",
            "system.scaffolding",
            "system.fallback_routing",
        ):
            require_text(claim, path, errors, claim_id)

        result_value = field(claim, "result.value", errors, claim_id)
        if result_value is None or isinstance(result_value, (dict, list, bool)):
            errors.append(f"{claim_id}: result.value must be a number or concise string")
        direction = field(claim, "result.direction", errors, claim_id)
        if direction is not None and direction not in DIRECTIONS:
            errors.append(f"{claim_id}: result.direction must be higher or lower")

        tools = field(claim, "system.tools", errors, claim_id)
        if tools is not None and (
            not isinstance(tools, list) or not all(isinstance(item, str) for item in tools)
        ):
            errors.append(f"{claim_id}: system.tools must be a list of strings")

        limitations = claim.get("limitations")
        if not isinstance(limitations, list) or not all(
            isinstance(item, str) and item.strip() for item in limitations
        ):
            errors.append(f"{claim_id}: limitations must be a list of non-empty strings")

        status = claim.get("status")
        if status not in STATUSES:
            errors.append(f"{claim_id}: status is invalid")

        relationships = validate_evidence(
            claim.get("evidence"),
            claim_id,
            max_source_age_days,
            errors,
            warnings,
        )
        if "vendor" in relationships and not (
            {"independent", "benchmark-owner"} & relationships
        ):
            warnings.append(
                f"{claim_id}: vendor-only evidence has no benchmark-owner or independent support"
            )
        if status == "verified" and relationships == {"unknown"}:
            warnings.append(f"{claim_id}: verified status relies only on an unknown publisher relationship")

    return errors, warnings


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("register", type=Path, help="claim-register JSON file")
    result.add_argument(
        "--max-source-age-days",
        type=int,
        default=30,
        help="warn when a source was accessed longer ago (default: 30)",
    )
    result.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.max_source_age_days < 0:
        print("ERROR: --max-source-age-days cannot be negative", file=sys.stderr)
        return 2
    try:
        data = json.loads(args.register.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read register: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate(data, args.max_source_age_days)
    report = {"status": "PASS" if not errors else "FAIL", "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['status']}: AI benchmark claim register")
        for error in errors:
            print(f"  FAIL: {error}")
        for warning in warnings:
            print(f"  NOTE: {warning}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
