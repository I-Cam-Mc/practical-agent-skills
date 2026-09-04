---
name: docker-deliverable-preflight
description: Preflight a Docker or OCI deliverable before hand-off, including clean-package replay, runtime isolation, artefact integrity, and honest reporting of blocked checks.
---

# Docker Deliverable Preflight

Turn an intended container hand-off into a small, observable release contract, then test the distributable rather than trusting the working directory.

## Establish the contract

Identify:

- the exact directory or archive being delivered;
- the documented recipient command;
- supported platforms and architectures;
- whether the workload genuinely needs network, host files, elevated privileges, or persistent writes;
- which outputs, checksums, software bill of materials (SBOM), provenance, runtime and vulnerability claims the hand-off makes.

Do not silently strengthen or weaken product requirements. Treat isolation controls as conditional on the workload. An offline one-shot job should normally use the isolated profile below. A network service needs a task-specific network contract instead.

## Verify in layers

1. Run static checks. Confirm package completeness, digest-pinned base images, a non-root final user, valid scripts, and the absence of obvious host-socket or privileged runtime access.
2. Build for every claimed architecture when the local builder supports it. Record commands and image identifiers from the current run.
3. Exercise the documented recipient command. Verify exit behaviour, required outputs and failure messages through public interfaces.
4. For an offline one-shot container, verify `--network=none`, a read-only root filesystem, all capabilities dropped, no-new-privileges, process and resource limits, purpose-specific writable mounts, and no Docker socket or broad host bind mount.
5. Check generated evidence. Recalculate checksums. Validate the SBOM or attestation structurally before describing it as useful evidence.
6. Package the deliverable, extract it into a new temporary directory, and rerun the same release contract there. This clean replay is the hand-off proof.

Use `python3 scripts/verify_container_delivery.py TARGET --profile basic` for the portable static checks. Use `--profile isolated` only when the deliverable claims an offline hardened runtime. The script does not build an image, execute the workload, scan for vulnerabilities, or prove that a generated SBOM is accurate.

## Report evidence honestly

Report each check as `PASS`, `FAIL`, `BLOCKED`, or `NOT APPLICABLE` with the current command or observation. A missing scanner, unavailable architecture, authentication failure, or disabled Docker daemon is `BLOCKED`, never `PASS`. Do not call a release ready while a claimed property remains unverified.

Do not push an image, publish an archive, change a registry, sign with a real key, or disclose build secrets unless the user explicitly requested that exact external action.

For the detailed contract, read [references/release-contract.md](references/release-contract.md).
