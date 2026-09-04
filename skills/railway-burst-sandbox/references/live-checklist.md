# Live checklist

## Before proposing a mutation

- Read Railway's current Sandbox, CLI, Priority Boarding, limits and pricing documentation.
- Record the access date and official URLs.
- Check the installed CLI version and current `sandbox --help` output.
- Confirm existing authentication without printing credentials.
- Resolve the exact workspace, project and environment through read-only output.
- List existing sandboxes and checkpoints before estimating capacity or cleanup.
- Define purpose, success condition, expected duration and stop condition.
- Choose resources and network access from workload evidence.
- Set an explicit short idle timeout and user-owned cost ceiling.
- Show the proposed create and cleanup operations for approval.

## Plan record

A plan consumed by `scripts/validate_sandbox_plan.py` has this shape. This is a
synthetic, runnable example. Replace the access date, labels, limits and evidence
with current values before using it for a real proposal.

```json
{
  "purpose": "Run one bounded synthetic test and collect its report",
  "target": {
    "project": "example-project",
    "environment": "temporary-sandbox"
  },
  "docs": {
    "checked_at": "2026-09-05",
    "urls": [
      "https://docs.railway.com/sandboxes",
      "https://docs.railway.com/cli/sandbox",
      "https://docs.railway.com/pricing"
    ]
  },
  "lifecycle": {
    "idle_timeout_minutes": 30,
    "explicit_destroy": true,
    "verify_absent_after_destroy": true,
    "success_condition": "The synthetic test report exists and parses",
    "stop_condition": "Stop after one attempt or twenty minutes"
  },
  "network": {
    "mode": "isolated",
    "justification": ""
  },
  "cost_control": {
    "currency": "AUD",
    "maximum_estimated_amount": 1.0,
    "estimate_basis": "Synthetic current-rate fixture; recalculate before use"
  },
  "approval": {
    "create": "pending",
    "destroy": "pending",
    "scope": "Create and destroy one synthetic sandbox in the named environment"
  }
}
```

Do not put tokens, IDs, private variables or account details in a plan intended for publication or chat. Keep exact identifiers in the authenticated tool call when needed.

## After an approved run

- Confirm the command result, including exit code and timeout state.
- Copy out and verify only the required artefacts.
- Destroy under the approved scope.
- List again and confirm the target is absent.
- State actual runtime and cost evidence only when obtained from current authenticated usage data.
- Report residual resources, unverified costs or cleanup failures plainly.
