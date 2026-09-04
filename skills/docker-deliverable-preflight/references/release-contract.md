# Release contract

Use only the sections relevant to the deliverable's stated claims.

## Package and build

- The recipient command and prerequisites are explicit.
- Required source, configuration and licence files are present.
- Base images are immutable by digest unless the project documents why they cannot be.
- The final image declares a non-root user.
- Claimed platforms are built from the release input, not inferred from a prior tag.
- Build secrets do not appear in Dockerfile layers, logs or the final image configuration.

## Runtime

For an offline one-shot workload, verify the effective runtime configuration:

- no network namespace connectivity;
- read-only root filesystem;
- all Linux capabilities dropped;
- no-new-privileges set;
- bounded processes, memory and CPU;
- only narrow writable `tmpfs` or managed volumes;
- no Docker socket, privileged mode, host PID namespace or broad host bind mount;
- the configured user and group are not root;
- termination signals produce the documented result and cleanup.

Do not impose `--network=none` on a service whose product requirements include networking. Define an explicit allowlist or task-specific network test instead.

## Outputs and evidence

- Required outputs exist, are non-empty and can be consumed by their intended reader.
- Recorded hashes are recalculated from the final files.
- An SBOM parses as its claimed format and refers to the released image or files.
- Provenance or attestation identifies the actual release input and subject digest.
- A vulnerability scan records tool, database timestamp, target digest and result.
- If a scanner cannot run, the release report says `BLOCKED` or `UNVERIFIED`.

## Clean replay

1. Create the archive from the intended release contents.
2. Reject absolute paths, parent traversal, device files and unexpected links before extraction.
3. Extract into a new temporary directory.
4. Run the documented recipient command and the same release checks.
5. Compare required outputs and current hashes with the contract.
6. Retain only the report and intended artefact, then clean temporary resources.

The working tree passing is development evidence. The clean replay passing is hand-off evidence.
