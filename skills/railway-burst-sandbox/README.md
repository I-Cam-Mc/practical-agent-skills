# Railway Burst Sandbox

A conservative Codex skill for temporary compute on Railway Sandboxes.

It defaults to a plan and read-only inspection. Creation, billing-affecting changes, checkpoint replacement and destruction all require explicit approval for the exact target. After an approved run, it verifies the result, destroys the sandbox within the approved cleanup scope, and lists again to catch resources still accruing cost.

Railway Sandboxes are evolving. At packaging time, Railway documented them as available through its beta Priority Boarding program and warned that breaking changes may occur. Always verify the [Sandbox documentation](https://docs.railway.com/sandboxes), [CLI reference](https://docs.railway.com/cli/sandbox), [Priority Boarding status](https://docs.railway.com/platform/priority-boarding) and [pricing](https://docs.railway.com/pricing) immediately before use.

## Install

```sh
cp -R railway-burst-sandbox "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex, then ask it to use `$railway-burst-sandbox` to plan or inspect a short-lived workload.

## Optional plan validator

The validator is offline and uses only Python's standard library:

```sh
python3 scripts/validate_sandbox_plan.py /path/to/plan.json
```

It validates the plan record. It does not authenticate, query Railway, estimate current pricing, create infrastructure, or turn an `approved` field into actual authority.

## Test

```sh
python3 -m unittest discover -s tests -v
```

## Licence

MIT. See [LICENSE](LICENSE).
