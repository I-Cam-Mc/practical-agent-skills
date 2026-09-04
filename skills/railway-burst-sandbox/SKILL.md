---
name: railway-burst-sandbox
description: Plan, inspect, create, verify, and clean up short-lived Railway Sandboxes with explicit approval gates, current-doc checks, and cost-aware lifecycle controls.
---

# Railway Burst Sandbox

Use Railway Sandboxes as temporary compute, not as an assumed always-on server. Default to planning and read-only inspection.

## Start with current evidence

Before every use, read Railway's current official documentation for [Sandboxes](https://docs.railway.com/sandboxes), the [`railway sandbox` command](https://docs.railway.com/cli/sandbox), [Priority Boarding](https://docs.railway.com/platform/priority-boarding), and [pricing](https://docs.railway.com/pricing). Check the installed CLI's `railway sandbox --help` as well.

Sandboxes were available through Railway's beta Priority Boarding program when this skill was packaged, and Railway warned that breaking changes may occur. Treat that as dated context, not a permanent fact. Reconfirm availability, limits, flags, SDK behaviour and rates live. Do not copy commands from this skill if current official documentation differs.

## Safe default

Without explicit mutation approval:

- clarify the workload, duration, target project and environment;
- inspect existing authentication, CLI capability, sandbox list, limits and current usage using read-only commands;
- produce a proposed lifecycle, resource shape, network mode, cost ceiling, timeout, verification and cleanup plan;
- show the exact commands or API operations that would mutate Railway;
- stop before creation, checkpoint replacement, network changes, billing-affecting actions or destruction.

Never infer payer identity from workspace access or administrator status. Never expose tokens, environment values, project identifiers or account details in chat, logs, generated examples or a repository.

## Approval gates

Obtain explicit approval for the exact target and operation immediately before:

- creating or forking a sandbox;
- building a template or checkpoint when it stores billable state;
- changing resources, network access, idle timeout or other billing-affecting settings;
- destroying a sandbox or deleting/replacing a checkpoint.

An approved plan may cover creation and its paired cleanup when it names both actions and the exact target. Otherwise, pause again before destruction. A plan file records intent but is not proof of approval.

## Lifecycle after approval

1. Resolve and read back the authenticated workspace, project and environment. Stop on ambiguity.
2. Recheck the sandbox list so the baseline and limits are known.
3. Create one sandbox with the smallest justified resources, an explicit short idle timeout and the narrowest network access that works.
4. Confirm it reaches the documented ready state before executing work.
5. Run commands with timeouts. Inspect exit code, timeout, truncation, stdout and stderr rather than trusting output alone.
6. Verify the intended result and copy out only required artefacts. Do not put secrets into per-command arguments or logs.
7. Use a checkpoint only when its reuse value justifies stored state. Remember that files persist across checkpoint or fork, while running processes do not.
8. Destroy the sandbox under the approved cleanup scope.
9. List sandboxes again and verify the target is gone. Report any residual sandbox or checkpoint as a live cost risk.

If execution is interrupted, preserve the sandbox identifier privately and surface cleanup as required user action. Do not create replacement sandboxes repeatedly after the same failure.

Use `python3 scripts/validate_sandbox_plan.py PLAN.json` to check that a proposed plan contains the important lifecycle, evidence and approval fields. The validator does not contact Railway and cannot grant permission.

For the live-check sequence and plan shape, read [references/live-checklist.md](references/live-checklist.md).
