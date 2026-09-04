---
name: web-release-proof
description: Implement and verify a scoped website change through local checks, desktop and mobile previews, deployment evidence and production readback. Use when completion depends on proving the live user-visible result, not for general site design.
---

# Web Release Proof

Close the gap between a local edit and a released website change.

## Define the release claim

Record the exact page, component, requested behaviour, excluded nearby changes, target environment and acceptance evidence. Link the work item when the repository uses an issue tracker.

## Implement within scope

- Inspect repository instructions and existing patterns first.
- Make the smallest coherent change.
- Preserve unrelated user work.
- Run the narrowest relevant tests, lint and build checks.
- Do not broaden a footer-only, route-only or copy-only request to adjacent surfaces without approval.

## Preview the actual result

Render the changed surface at representative desktop and mobile widths. Check content, layout, overflow, interaction, focus, contrast and console errors. A source diff is not a visual preview.

## Verify production

After an authorised deployment, verify:

- the expected deployment or commit is serving;
- the production URL returns the intended page;
- the changed content or behaviour is visible on desktop and mobile;
- there are no new console or network failures on the changed path;
- cached or stale output is not being mistaken for the release.

Local tests, a successful build and a green deployment record do not individually prove the user-visible outcome. Do not close the work item until production readback passes. If deployment is outside the user's request or authority is missing, report the local result as ready for release, not released.
