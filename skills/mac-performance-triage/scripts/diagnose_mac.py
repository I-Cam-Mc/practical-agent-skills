#!/usr/bin/env python3
"""Collect bounded, read-only macOS CPU and memory evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from collections import defaultdict
from typing import Sequence


MAX_INTERVAL_SECONDS = 30.0
MAX_TOP_PROCESSES = 20


def _run(args: Sequence[str], timeout: float = 12.0) -> str | None:
    try:
        completed = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def parse_top_cpu(text: str) -> dict[str, float] | None:
    matches = re.findall(
        r"CPU usage:\s*([0-9.]+)% user,\s*([0-9.]+)% sys,\s*([0-9.]+)% idle",
        text,
    )
    if not matches:
        return None
    user, system, idle = (float(value) for value in matches[-1])
    return {"user_percent": user, "system_percent": system, "idle_percent": idle}


def _size_bytes(value: float, unit: str) -> int:
    factors = {
        "B": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }
    return int(value * factors[unit.upper()])


def parse_swapusage(text: str) -> dict[str, int] | None:
    match = re.search(
        r"total\s*=\s*([0-9.]+)([BKMGTP])\s+used\s*=\s*"
        r"([0-9.]+)([BKMGTP])\s+free\s*=\s*([0-9.]+)([BKMGTP])",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    total, total_unit, used, used_unit, free, free_unit = match.groups()
    return {
        "total_bytes": _size_bytes(float(total), total_unit),
        "used_bytes": _size_bytes(float(used), used_unit),
        "free_bytes": _size_bytes(float(free), free_unit),
    }


def parse_pressure_level(text: str) -> str:
    try:
        value = int(text.strip(), 0)
    except ValueError:
        return "unknown"
    return {1: "normal", 2: "warning", 4: "critical"}.get(value, "unknown")


def parse_free_percent(text: str) -> float | None:
    match = re.search(r"System-wide memory free percentage:\s*([0-9.]+)%", text)
    return float(match.group(1)) if match else None


def parse_load_averages(text: str) -> list[float] | None:
    match = re.search(r"load averages?:\s*([0-9.]+)[, ]+([0-9.]+)[, ]+([0-9.]+)", text)
    if not match:
        return None
    return [float(value) for value in match.groups()]


def parse_processes(text: str, limit: int) -> list[dict[str, object]]:
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"cpu_percent": 0.0, "rss_bytes": 0.0, "process_count": 0.0}
    )
    for line in text.splitlines():
        match = re.match(r"\s*([0-9.]+)\s+(\d+)\s+(.+?)\s*$", line)
        if not match:
            continue
        cpu, rss_kib, command = match.groups()
        name = os.path.basename(command) or "unknown"
        totals[name]["cpu_percent"] += float(cpu)
        totals[name]["rss_bytes"] += float(rss_kib) * 1024
        totals[name]["process_count"] += 1

    ranked = sorted(
        totals.items(),
        key=lambda item: (item[1]["rss_bytes"], item[1]["cpu_percent"]),
        reverse=True,
    )[:limit]
    return [
        {
            "name": name,
            "cpu_percent": round(values["cpu_percent"], 2),
            "rss_bytes": int(values["rss_bytes"]),
            "process_count": int(values["process_count"]),
        }
        for name, values in ranked
    ]


def _sysctl(name: str) -> str | None:
    return _run(["/usr/sbin/sysctl", "-n", name], timeout=5)


def cpu_snapshot() -> dict[str, float] | None:
    output = _run(["/usr/bin/top", "-l", "2", "-s", "1", "-n", "0"])
    return parse_top_cpu(output) if output else None


def collect(interval: float, top_processes: int) -> dict[str, object]:
    unavailable: list[str] = []

    first_cpu = cpu_snapshot()
    if first_cpu is None:
        unavailable.append("first CPU observation")

    pressure_raw = _sysctl("kern.memorystatus_vm_pressure_level")
    pressure = parse_pressure_level(pressure_raw) if pressure_raw else "unavailable"
    if pressure == "unavailable":
        unavailable.append("memory pressure level")

    swap_raw = _sysctl("vm.swapusage")
    swap = parse_swapusage(swap_raw) if swap_raw else None
    if swap is None:
        unavailable.append("swap usage")

    free_output = _run(["/usr/bin/memory_pressure", "-Q"], timeout=8)
    free_percent = parse_free_percent(free_output) if free_output else None
    if free_percent is None:
        unavailable.append("memory free percentage")

    logical_raw = _sysctl("hw.logicalcpu")
    logical_cpus = int(logical_raw.strip()) if logical_raw and logical_raw.strip().isdigit() else None
    if logical_cpus is None:
        unavailable.append("logical CPU count")

    load_output = _run(["/usr/bin/uptime"], timeout=5)
    load_averages = parse_load_averages(load_output) if load_output else None
    if load_averages is None:
        unavailable.append("load averages")

    if interval:
        time.sleep(interval)
    second_cpu = cpu_snapshot()
    if second_cpu is None:
        unavailable.append("second CPU observation")

    processes: list[dict[str, object]] | None = None
    if top_processes:
        process_output = _run(
            ["/bin/ps", "-A", "-o", "pcpu=,rss=,comm="], timeout=8
        )
        if process_output:
            processes = parse_processes(process_output, top_processes)
        else:
            unavailable.append("process summary")

    available_count = sum(
        value is not None and value != "unavailable"
        for value in (
            first_cpu,
            second_cpu,
            pressure,
            swap,
            free_percent,
            logical_cpus,
            load_averages,
        )
    )
    return {
        "status": "complete" if not unavailable else ("partial" if available_count else "unavailable"),
        "read_only": True,
        "cpu_observations": [value for value in (first_cpu, second_cpu) if value],
        "memory_pressure": pressure,
        "memory_free_percent": free_percent,
        "swap": swap,
        "logical_cpu_count": logical_cpus,
        "load_averages": load_averages,
        "top_processes": processes,
        "unavailable_probes": unavailable,
        "interpretation_notes": [
            "One CPU spike does not establish sustained load.",
            "Memory pressure is more actionable than raw used-memory percentage.",
            "Swap may remain allocated after memory pressure eases.",
        ],
    }


def _gib(value: int) -> float:
    return value / 1024**3


def format_human(report: dict[str, object]) -> str:
    lines = [f"Collection status: {report['status']}"]
    observations = report["cpu_observations"]
    if isinstance(observations, list) and observations:
        for index, observation in enumerate(observations, start=1):
            lines.append(
                f"CPU observation {index}: {observation['idle_percent']:.1f}% idle "
                f"({observation['user_percent']:.1f}% user, "
                f"{observation['system_percent']:.1f}% system)"
            )
    else:
        lines.append("CPU observations: unavailable")

    lines.append(f"Memory pressure: {report['memory_pressure']}")
    free_percent = report.get("memory_free_percent")
    if isinstance(free_percent, (int, float)):
        lines.append(f"System-wide memory free: {free_percent:.1f}%")

    swap = report.get("swap")
    if isinstance(swap, dict):
        lines.append(
            f"Swap used: {_gib(swap['used_bytes']):.2f} GiB of "
            f"{_gib(swap['total_bytes']):.2f} GiB"
        )
    else:
        lines.append("Swap usage: unavailable")

    loads = report.get("load_averages")
    cpus = report.get("logical_cpu_count")
    if isinstance(loads, list):
        suffix = f" across {cpus} logical CPUs" if isinstance(cpus, int) else ""
        lines.append("Load averages: " + ", ".join(f"{value:.2f}" for value in loads) + suffix)

    processes = report.get("top_processes")
    if isinstance(processes, list):
        lines.append("Optional process summary:")
        for process in processes:
            lines.append(
                f"  {process['name']}: {process['rss_bytes'] / 1024**2:.0f} MiB RSS, "
                f"{process['cpu_percent']:.1f}% CPU, {process['process_count']} process(es)"
            )

    unavailable = report.get("unavailable_probes")
    if isinstance(unavailable, list) and unavailable:
        lines.append("Unavailable probes: " + ", ".join(unavailable))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect bounded, read-only macOS performance evidence."
    )
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--top-processes", type=int, default=0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if platform.system() != "Darwin":
        print("This helper requires macOS.", file=sys.stderr)
        return 2
    if not 0 <= args.interval <= MAX_INTERVAL_SECONDS:
        print(
            f"--interval must be between 0 and {MAX_INTERVAL_SECONDS} seconds.",
            file=sys.stderr,
        )
        return 2
    if not 0 <= args.top_processes <= MAX_TOP_PROCESSES:
        print(
            f"--top-processes must be between 0 and {MAX_TOP_PROCESSES}.",
            file=sys.stderr,
        )
        return 2

    report = collect(args.interval, args.top_processes)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_human(report))
    return 1 if report["status"] == "unavailable" else 0


if __name__ == "__main__":
    raise SystemExit(main())
