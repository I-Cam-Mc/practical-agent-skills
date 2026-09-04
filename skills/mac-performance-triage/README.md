# mac-performance-triage

A read-only Codex skill for answering a deceptively difficult question: is a
Mac slow because of sustained CPU demand, current memory pressure, accumulated
swap, or something the snapshot cannot establish?

The helper captures two CPU observations, current memory-pressure signals,
swap and load. It does not quit apps, kill processes, clear caches or create
artificial memory pressure. Process names are excluded by default.

## Install

Copy this directory to `~/.codex/skills/mac-performance-triage`, then restart
Codex.

## Use with Codex

```text
Use $mac-performance-triage to assess why this Mac feels slow. Keep it read-only.
```

## Use the helper directly

```bash
python3 scripts/diagnose_mac.py
python3 scripts/diagnose_mac.py --json
```

App-level attribution is optional because names can be sensitive when a report
is shared:

```bash
python3 scripts/diagnose_mac.py --top-processes 8
```

Requirements: macOS and Python 3. Some restricted automation environments may
block process and kernel telemetry. The helper reports a partial result rather
than pretending unavailable probes succeeded.

## Reading the result

- Two similar low-idle CPU observations are stronger evidence than one spike.
- macOS memory-pressure state is more useful than a raw used-memory percentage.
- Swap can remain allocated after pressure eases, so swap alone does not prove
  the Mac is currently constrained.
- Load average should be interpreted relative to logical CPU count.

The skill deliberately avoids universal red-line thresholds. Workload shape,
hardware and the user's actual symptoms matter.

## Verify

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

## Licence

MIT
