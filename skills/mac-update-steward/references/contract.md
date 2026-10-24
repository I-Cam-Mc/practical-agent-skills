# Helper contract, schema 1

All inputs are local operator/agent observations, not trusted remote commands.
They contain no executable instructions. A plan cannot grant permission. Do not
set a boolean to true just to obtain `ready`: retain the evidence establishing it.
The SHA-256 plan id detects edits, not malicious forgery. These helpers do not
replace host approval controls or independently authenticate vendor evidence.

## Policy and candidates

`plan --policy FILE --candidates FILE --output NEW_FILE` reads a policy object and
candidate array. Examples are fictional and default to no installation authority.
The output is exclusively created with mode 0600. Never store secrets in inputs.

Policy:

| Field | Meaning |
|---|---|
| `devices` | Exact operator-chosen aliases, not discovered machines to enrol |
| `install_authorized` | Boolean, true only when current user authority covers ordinary updates |
| `protected_ids` | Installation ids protected across all scoped devices |
| `approvals` | Exact migration targets approved by the user; empty by default |

Each candidate has:

| Field | Meaning |
|---|---|
| `device`, `id`, `name` | Scope alias, unique installation identity and display name |
| `before`, `target` | Actual installed and eligible offered version strings |
| `before_build`, `target_build` | Optional paired build numbers, including build-only updates |
| `owner` | Responsible updater, such as `vendor`, `homebrew`, `app-store`, `macos` or a runtime manager |
| `source_url` | Canonical public HTTPS provenance URL, no credentials or private query tokens |
| `change` | `patch` or `minor` for ordinary updates, otherwise a reviewed class such as `major`, `runtime-major`, `os-major`, `migration` or `unknown` |
| `channel` | Must be `stable` for readiness |
| `present` | Actual target installation exists, not only its receipt |
| `source_verified` | Official provenance and applicable authenticity checks established |
| `compatible` | OS, architecture, plug-ins, drivers and affected dependents checked |
| `eligible` | This installation's configured updater/channel offers this release |
| `idle` | Workload/unsaved-work checks passed, not merely low CPU |
| `rollback_ready` | Compatible recovery retained; stateful updates also need consistent data backup and restoration procedure |
| `protected` | Whether replacing/activating this target threatens current work/access |
| `pinned` | Explicit pin, preserved until separately resolved |
| `activation_required` | True when running/newly invoked version must match; false only for a closed app intentionally left closed |

Boolean facts accept `true`, `false` or `null`; missing/unknown readiness facts
hold the item. `protected` and `pinned` must explicitly be false. Missing
`activation_required` requires running verification.

Versions are compared conservatively as up to eight integer components. Calendar
versions and integer builds can be ordered, but a leading-component change still
requires review. Unrecognised formats (`latest`, version-plus-build strings,
prerelease labels) are held rather than guessed. Separate version/build fields
where possible; exact strings must match when verifying. A pre-1.0 second-component
change is a migration decision, even if labelled `patch`.

An exact approval object contains all fields returned by `approval_target(candidate)`:
`device`, `id`, `before`, `target`, `before_build`, `target_build`, `source_url`,
`change`, `owner`. Omitted build values are explicit JSON null. It waives only the
migration-class review, not authority, source, idle, pin, protection, compatibility
or rollback checks. Bind it to the actual user's decision; do not generate approval
by copying a candidate without that authority.

The item decisions are `ready`, `defer`, `review` and `skip`, with stable reason
codes. `ready` is a policy result, not an execution permit issued by the tool.

## Fresh preflight

`check --plan FILE --candidates REFRESHED_FILE` rejects plans older than 24 hours,
future timestamps, edits, inconsistent decisions or any changed candidate facts.
Refresh the observations on the actual target immediately before an agent invokes
its supported updater. The helper cannot prove that a copied input is fresh. It
neither installs software nor creates a check-to-install lock.

## Results and journal

`record --plan FILE --results FILE --state-dir PRIVATE_DIRECTORY` reconciles a
result array. Do not submit results for skipped/held items. No result for a ready
item becomes `coverage_gap`, never a successful empty check. Unknown devices and
duplicate identities are rejected.

An installed-result example (all values fictional):

```json
{
  "device": "workstation",
  "id": "example.editor",
  "before": "2.4.0",
  "phase": "installed",
  "observed_at": "2030-01-01T10:01:00+00:00",
  "installed_version": "2.4.1",
  "running_version": "2.4.1",
  "identity_matches": true,
  "functional_ok": true,
  "restart_required": false,
  "evidence": ["/private/tmp/example-verification.txt"]
}
```

Use the actual observation time, after plan creation and no later than now.
Include `before_build`, `installed_build` and `running_build` when the candidate
uses build numbers. `before` is the immediate pre-install observation. A mismatch
is `stale_plan`, not an update credited to this run.

Other phases: `downloaded`, `staged`, `failed`, `blocked`, `unavailable`. Use a
short `reason` code (`account_authentication_required`, `updater_timeout`, etc.),
not raw command output. Installed observations require identity, exact version,
functional verification and nonempty local evidence files to reach `verified`.
A required restart produces `pending_restart`; an unmatched/unverified running
version produces `pending_relaunch`. Neither counts as verified. For OS payloads
only prepared/downloaded, use that phase even if the updater suggests a restart.

Evidence paths are hashed without embedding their contents. Existence and a hash
prove which file was referenced, not that its assertions are true. Keep evidence
private, sanitise credentials before saving any logs, and preserve the raw-data
boundary. The journal stores local paths and app identities and is not suitable
for public upload without a separate review. Missing or empty evidence files fail
recording; an empty evidence array produces verification failure.

SQLite serialises journal writes and commits each run atomically. The state file
is created mode 0600; existing non-private directories/files or symlinks are refused. Use a
private local directory, not a shared filesystem. Concurrent writes fail promptly.
This lock does not cover agent installation commands. Prevent overlapping jobs in
the scheduler. After an interrupted installation, inspect actual installed and
running state before attempting it again.

A repeated plan with identical evidence is a replay and produces no changes.
Different evidence on the same plan is refused; make a fresh plan for later
observations. Across plans, only changed target/build, state or reason triggers a
notification. Skipped items are retained but quiet. `record --all` prints a receipt
even when unchanged. `status --state-dir DIRECTORY` reads the latest known findings,
including their last observation times; these are history, not a fresh audit.

The journal preserves `before_build`, `target_build` and result `observed_at`.
`first_recorded_at` and `last_recorded_at` are separate recording timestamps.
Held items with no result have no verified observation time. A pending restart
still requires identity and nonempty evidence; it does not certify the target
version until the reboot and verification have actually happened.

### Device and source coverage

Pass `record --coverage coverage.json` to retain gaps even when a device has no
known app candidates. Example entry (array at the file root):

```json
{
  "device": "studio",
  "source": "device",
  "state": "unavailable",
  "reason": "connection_unavailable",
  "observed_at": "2030-01-01T10:01:00+00:00"
}
```

Use a policy-scoped device and a real observation within 24 hours. Sources are
`device`, `macos`, `homebrew`, `app-store`, `runtimes`, `vendor`; states are
`checked`, `partial`, `unavailable`. A checked vendor source means the specified
scope was checked, not that every possible vendor is known. These entries use
reserved ids beginning `coverage:`. Normal installation ids cannot use that
prefix. Duplicate coverage entries and unscoped devices are rejected.

Record each relevant source per device on every run, including unreachable ones.
The helper cannot know which sources the operator forgot to check. Initial healthy
checks are quiet, new/changed gaps are reported, and recovery from a previous gap
is reported. Unmentioned sources retain historical records, not fresh coverage.
Cooldowns and update attempt budgets are enforced by the agent/scheduler, not this
journal. Inspect the latest reason and relevant changed conditions before retrying.

## Coverage and portability

`inventory.py --output NEW_FILE` inspects local bundles and allowlisted invoked
runtimes. `--app-root` and `--runtime` may repeat and replace their defaults.
`--timeout` is finite, greater than zero and at most 60 seconds. Each probe has
bounded time/output and terminates only its own process group on a timeout or
output overflow. The tool does not infer running-process versions, app idleness,
manager offers, source authenticity or completeness of application coverage.

CLI/helper tests run with Python 3.9+ on macOS/Linux. Actual updater operations and
macOS metadata need macOS. Remote orchestration remains the agent's responsibility
through an already authenticated SSH connection; no machine names or credentials
are embedded in the package.
