---
name: personal-data-approval-pack
description: Prepare approval-gated personal-data maintenance for contacts, calendars, notes or credential metadata. Use when a cleanup, merge, import or deletion request needs read-only discovery, exact review rows, backup evidence and post-write readback before any mutation.
---

# Personal Data Approval Pack

Turn an imprecise personal-data request into a bounded, reviewable change set.

## Start read-only

1. State the requested outcome, systems in scope and systems explicitly out of scope.
2. Identify the canonical destination and preserve source-account provenance.
3. Inventory records, access state and available supported export or backup routes.
4. Retrieve only the fields needed for the decision. Do not collect credential values, recovery codes or unrelated message/note bodies.
5. Separate exact matches, plausible overlaps, ambiguous identities and conflicts.

Shared identifiers are overlap evidence, not identity proof. Never merge people solely because they share a phone number, address, organisation or family account.

## Produce the approval pack

Use [assets/approval-pack-template.md](assets/approval-pack-template.md). Include:

- current state and source counts;
- canonical destination and preservation rules;
- proposed operations with stable IDs;
- before and after fields for every operation;
- ambiguous rows and the precise question each needs answered;
- backup format, location, timestamp, count and checksum plan;
- dry-run checks and stop conditions;
- post-write readback checks;
- an explicit statement that no live change has occurred.

Follow [references/mutation-manifest.md](references/mutation-manifest.md) for machine-readable operations.

## Mutation gate

Do not execute a live import, merge, link, edit, deletion, password change, passkey migration or calendar write until the user approves the exact manifest and destination.

Immediately before execution:

- refresh the source state;
- create supported backups and record their hashes and counts;
- stop if the approved before-state no longer matches;
- use supported application or API routes, never direct edits to an application's private database.

Apply changes in small batches, preferably one identity at a time when ambiguity exists. Read back after each batch. Stop on field loss, wrong account, unexpected duplicate, identifier mismatch or unsupported UI/API state.

## Completion evidence

Local files, dry runs and valid import packages are not proof of a live result. Verify the destination's ownership, privacy, timezone, record count, field values, recurrence and alerts as applicable. Report any portion that remains unverified.

For credential stores, remain metadata-only unless the user explicitly requests a specific credential action. Never print, persist or transmit secrets.
