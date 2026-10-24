# Mac Update Steward

An agent skill for keeping Macs up to date while preserving active work, remote
access and evidence of what actually changed. MIT licensed. Python 3.9+, standard
library only. macOS is required for live inventory and updates; synthetic tests
also run on Linux.

## Why a skill first?

App Store authentication, vendor rollout eligibility, runtime migrations and
unsaved work need different checks. This package gives an agent a repeatable
workflow and small tools for the parts that can be deterministic. It is not a
universal unattended installer or a privileged background daemon.

- **Inventory**: actual bundles and invoked runtime paths, with explicit gaps.
- **Plan**: authority, compatibility, rollout, protected workloads and exact-version checks.
- **Verify**: installed and running versions, build numbers, functional evidence.
- **Remember**: private transactional journal, replay protection and quiet unchanged runs.

## Install and use

Copy this whole folder into your agent's skills directory, or use its GitHub
skill installer for `skills/mac-update-steward` in this repository. Then ask:

> Use $mac-update-steward to audit this Mac and prepare compatible stable updates.

For an existing authorised recurring workflow:

> Use $mac-update-steward to complete the approved updates on my named Macs.
> Preserve active work and the agent's connection, and report only changes.

The skill does not install a schedule. Review and authorise the devices, update
classes and relaunch policy once; keep that private configuration with your
scheduler. The examples grant no installation authority.

## Try the helpers without installing software

From this folder, with a fresh temporary output directory:

```bash
python3 scripts/steward.py plan --candidates examples/candidates.json --policy examples/policy.json --output /private/tmp/steward-plan.json
python3 scripts/steward.py record --plan /private/tmp/steward-plan.json --results examples/no-results.json --state-dir /private/tmp/steward-state
```

This synthetic example is held for review. Recording it again prints nothing.
For a local bundle/runtime snapshot, use `inventory.py --output` with a new private
path. Review [SKILL.md](SKILL.md) for the agent workflow, [contract](references/contract.md)
for the JSON interfaces and [backend notes](references/updaters.md) for official
updater documentation.

## Improvements over an ad hoc update script

The planner rejects missing apps, downgrades, stale facts, unknown eligibility,
protected access paths and migrations lacking exact approval. Completion has
separate downloaded, staged, installed, pending-relaunch, pending-restart and
verified states. The journal retains evidence hashes without copying logs and
deduplicates unchanged failures. Local output is private; public examples are
fictional and contain no machine inventory or account credentials.

## Verify the package

```bash
python3 -m unittest discover -s tests -v
```

Tests cover synthetic bundles, owned-process timeouts/output limits, policy,
version/build ordering, migration approvals, stale plans, verification states and
journal replay. These do not certify every vendor updater or a complete live
installation. Live updates are performed by the agent using existing official
updaters, not by the Python helpers. No telemetry or network service is included.

A future application could wrap these interfaces in a review UI and add individual
installer adapters with dedicated recovery tests. Ship those adapters only after
end-to-end testing on disposable Macs, including interrupted installations.
