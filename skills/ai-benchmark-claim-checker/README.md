# AI Benchmark Claim Checker

A Codex skill for checking what an AI benchmark result actually supports.

It separates task design from the headline number, explains score semantics, records the evaluated system rather than just a model name, and distinguishes vendor claims from benchmark-owner and independent evidence. It also catches routed systems and fallback models that can otherwise be mistaken for a standalone model result.

## Install

```sh
cp -R ai-benchmark-claim-checker "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex, then invoke `$ai-benchmark-claim-checker` with a claim, comparison, leaderboard or source.

## Claim-register validator

The optional validator uses only Python's standard library:

```sh
python3 scripts/validate_claim_register.py /path/to/register.json
python3 scripts/validate_claim_register.py /path/to/register.json --max-source-age-days 7 --json
```

It checks whether each claim records task design, score meaning, configuration, fallback routing, source relationship and access date. It cannot establish that the source or conclusion is correct.

No benchmark questions, answer keys, evaluation datasets or copied vendor reports are included.

## Test

```sh
python3 -m unittest discover -s tests -v
```

## Licence

MIT. See [LICENSE](LICENSE).
