---
name: mac-performance-triage
description: Diagnose current macOS CPU, memory pressure, swap and load using bounded read-only observations. Use when a Mac feels slow or resource use needs explanation, not for automatic process cleanup or malware diagnosis.
---

# Mac Performance Triage

Collect current evidence before assigning a cause. Keep diagnosis separate from
remediation and do not mutate the Mac during triage.

## Collect

Run the bundled helper from this skill directory:

```bash
python3 scripts/diagnose_mac.py --json
```

It takes two CPU observations and reads memory pressure, swap and load without
creating load. Use `--top-processes N` only when app-level attribution is
needed. That option emits executable names, so leave it off when the result
will be shared publicly.

If a restricted environment blocks a probe, report it as unavailable. Do not
request administrator access merely to make a routine read-only report look
complete. Activity Monitor is a reasonable fallback when the user wants to
inspect the same evidence visually.

## Diagnose

- Treat one CPU spike as transient until a later observation supports it.
- Interpret load average relative to logical CPU count, not as a standalone
  percentage.
- Prefer macOS memory-pressure state over raw memory utilisation.
- Treat swap as accumulated paging. High swap can explain lingering
  responsiveness problems, but it does not prove pressure is currently high.
- Separate current evidence, inference and unknowns. Do not label a process as
  the cause merely because it appears once near the top.
- If both CPU and memory signals are healthy, say the snapshot did not capture
  the symptom and propose a bounded observation during the next slowdown.

## Recommend safely

Offer the least disruptive, reversible action that matches the evidence. Ask
before quitting apps, killing processes, restarting, changing login items or
moving work to another computer. Never automate those actions from this skill.

Do not present this triage as a malware scan, hardware diagnostic or proof of
thermal throttling. Use the relevant specialist workflow when those are the
actual questions.
