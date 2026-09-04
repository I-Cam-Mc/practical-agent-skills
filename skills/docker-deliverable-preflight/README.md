# Docker Deliverable Preflight

A Codex skill for verifying a Docker or OCI deliverable before it reaches someone else.

It turns release claims into observable checks, tests hardened offline runtimes, and reruns the hand-off from a cleanly extracted archive. It also keeps `blocked` distinct from `passed`, especially when a vulnerability scanner, builder or target architecture is unavailable.

## Install

Copy this folder to your Codex skills directory:

```sh
cp -R docker-deliverable-preflight "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex, then ask it to use `$docker-deliverable-preflight` on a project directory or release archive.

## Offline static verifier

The included Python script uses only the standard library:

```sh
python3 scripts/verify_container_delivery.py /path/to/package --profile basic
python3 scripts/verify_container_delivery.py /path/to/package.zip --profile isolated --json
```

`basic` checks archive safety, a readable Dockerfile, digest-pinned non-`scratch` bases, a non-root final user, shell syntax where available, and obvious unsafe runtime access. `isolated` additionally requires a documented runtime invocation with the expected offline isolation flags.

Static checks do not replace a current build, runtime test, SBOM validation or vulnerability scan.

## Test

```sh
python3 -m unittest discover -s tests -v
```

## Licence

MIT. See [LICENSE](LICENSE).
