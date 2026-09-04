#!/usr/bin/env python3
"""Measure selected Mac battery power telemetry without emitting raw ioreg data."""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from typing import Callable, Sequence


IOREG = "/usr/sbin/ioreg"
MAX_SAMPLES = 20
MAX_INTERVAL_SECONDS = 10.0


class MeasurementError(RuntimeError):
    """Raised when safe charging telemetry cannot be collected."""


@dataclass(frozen=True)
class PowerSample:
    system_input_w: float | None
    battery_power_w: float | None
    battery_current_a: float | None
    battery_voltage_v: float | None
    adapter_capacity_w: float | None
    adapter_name: str | None
    state: str


def _number(text: str, key: str) -> int | None:
    match = re.search(
        rf'"{re.escape(key)}"\s*=\s*(-?(?:0x[0-9a-fA-F]+|\d+))', text
    )
    if not match:
        return None
    return int(match.group(1), 0)


def _signed_64(value: int | None) -> int | None:
    if value is None:
        return None
    if value >= 1 << 63:
        return value - (1 << 64)
    return value


def _adapter_details(text: str) -> tuple[float | None, str | None]:
    match = re.search(r'"AdapterDetails"\s*=\s*\{(.*?)\}', text, re.DOTALL)
    if not match:
        return None, None
    details = match.group(1)
    watts = _number(details, "Watts")
    name_match = re.search(r'"Name"\s*=\s*"([^"\r\n]{1,120})"', details)
    return (
        float(watts) if watts is not None else None,
        name_match.group(1) if name_match else None,
    )


def parse_ioreg(text: str) -> PowerSample:
    """Parse only non-identifying fields needed for power calculations."""
    input_mw = _number(text, "SystemPowerIn")
    input_mv = _number(text, "SystemVoltageIn")
    input_ma = _signed_64(_number(text, "SystemCurrentIn"))
    battery_mv = _number(text, "Voltage")
    battery_ma = _signed_64(_number(text, "InstantAmperage"))
    adapter_w, adapter_name = _adapter_details(text)

    system_input_w: float | None = None
    if input_mw is not None:
        system_input_w = input_mw / 1000.0
    elif input_mv is not None and input_ma is not None:
        system_input_w = input_mv * input_ma / 1_000_000.0

    battery_power_w: float | None = None
    if battery_mv is not None and battery_ma is not None:
        battery_power_w = battery_mv * battery_ma / 1_000_000.0

    if battery_ma is None:
        state = "unknown"
    elif battery_ma > 0:
        state = "charging"
    elif battery_ma < 0:
        state = "discharging"
    else:
        state = "idle"

    if all(
        value is None
        for value in (system_input_w, battery_power_w, adapter_w, adapter_name)
    ):
        raise MeasurementError("No supported battery power fields were found.")

    return PowerSample(
        system_input_w=system_input_w,
        battery_power_w=battery_power_w,
        battery_current_a=(battery_ma / 1000.0 if battery_ma is not None else None),
        battery_voltage_v=(battery_mv / 1000.0 if battery_mv is not None else None),
        adapter_capacity_w=adapter_w,
        adapter_name=adapter_name,
        state=state,
    )


def read_ioreg() -> str:
    completed = subprocess.run(
        [IOREG, "-r", "-c", "AppleSmartBattery", "-l"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        raise MeasurementError(
            "macOS could not read AppleSmartBattery telemetry. "
            "No raw registry output was retained."
        )
    if not completed.stdout.strip():
        raise MeasurementError("No Mac laptop battery was found.")
    return completed.stdout


def collect_samples(
    count: int,
    interval: float,
    reader: Callable[[], str] = read_ioreg,
) -> list[PowerSample]:
    samples: list[PowerSample] = []
    for index in range(count):
        samples.append(parse_ioreg(reader()))
        if index + 1 < count and interval:
            time.sleep(interval)
    return samples


def _series(samples: Sequence[PowerSample], field: str) -> dict[str, float] | None:
    values = [getattr(sample, field) for sample in samples]
    available = [float(value) for value in values if value is not None]
    if not available:
        return None
    return {
        "median": round(statistics.median(available), 3),
        "minimum": round(min(available), 3),
        "maximum": round(max(available), 3),
    }


def summarise(samples: Sequence[PowerSample]) -> dict[str, object]:
    if not samples:
        raise MeasurementError("At least one sample is required.")
    states = [sample.state for sample in samples]
    state = statistics.mode(states)
    input_summary = _series(samples, "system_input_w")
    battery_summary = _series(samples, "battery_power_w")
    residual_w: float | None = None
    if input_summary and battery_summary and battery_summary["median"] >= 0:
        residual_w = round(
            input_summary["median"] - battery_summary["median"], 3
        )
        if residual_w < 0:
            residual_w = None

    adapter_names = [sample.adapter_name for sample in samples if sample.adapter_name]
    return {
        "sample_count": len(samples),
        "state": state,
        "adapter_name": adapter_names[0] if adapter_names else None,
        "adapter_capacity_w": _series(samples, "adapter_capacity_w"),
        "system_input_w": input_summary,
        "battery_power_w": battery_summary,
        "derived_system_and_conversion_w": residual_w,
        "telemetry_only": True,
    }


def _format_range(label: str, summary: object) -> str:
    if not isinstance(summary, dict):
        return f"{label}: unavailable"
    median = float(summary["median"])
    minimum = float(summary["minimum"])
    maximum = float(summary["maximum"])
    return f"{label}: {median:.1f} W median ({minimum:.1f} to {maximum:.1f} W)"


def format_human(summary: dict[str, object]) -> str:
    lines = [
        f"Samples: {summary['sample_count']}",
        f"Battery state: {summary['state']}",
    ]
    adapter_name = summary.get("adapter_name")
    if adapter_name:
        lines.append(f"Adapter model: {adapter_name}")
    lines.append(_format_range("Adapter-reported capacity", summary["adapter_capacity_w"]))
    lines.append(_format_range("System input", summary["system_input_w"]))
    lines.append(_format_range("Battery power", summary["battery_power_w"]))
    residual = summary.get("derived_system_and_conversion_w")
    if isinstance(residual, (int, float)):
        lines.append(f"Mac use plus conversion loss (derived): {residual:.1f} W")
    lines.append("Telemetry estimate only; this is not a wall-socket measurement.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure selected live Mac charging telemetry safely."
    )
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if platform.system() != "Darwin":
        print("This helper requires macOS.", file=sys.stderr)
        return 2
    if not 1 <= args.samples <= MAX_SAMPLES:
        print(f"--samples must be between 1 and {MAX_SAMPLES}.", file=sys.stderr)
        return 2
    if not 0 <= args.interval <= MAX_INTERVAL_SECONDS:
        print(
            f"--interval must be between 0 and {MAX_INTERVAL_SECONDS} seconds.",
            file=sys.stderr,
        )
        return 2

    try:
        summary = summarise(collect_samples(args.samples, args.interval))
    except (MeasurementError, subprocess.TimeoutExpired) as error:
        print(f"Unable to measure charging power: {error}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(format_human(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
