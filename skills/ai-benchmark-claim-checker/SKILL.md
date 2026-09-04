---
name: ai-benchmark-claim-checker
description: Verify and explain AI benchmark claims by separating task design, score semantics, system configuration, vendor evidence, independent evidence, effort, tools, and fallback routing.
---

# AI Benchmark Claim Checker

Use this skill when a benchmark number is being compared, repeated or used to support a practical decision. Explain what the work and score mean, not just who appears higher on a chart.

## Resolve the claim

Write the exact claim being checked. Identify the benchmark name and version, result date, evaluated system, reported score and source. If any are missing, keep them `unknown` rather than silently filling them from a similar run.

Benchmark results and product configurations can change. Search current primary sources for the methodology and the result on every substantive check. Prefer the benchmark owner's specification, result artefact or paper. Label vendor self-reports, benchmark-owner material and independent reproduction separately. Use secondary analysis only for context or when primary evidence is unavailable.

Do not reproduce private evaluation data, full benchmark tasks, long quotations or copyrighted prompt sets. Describe task categories and scoring in your own words.

## Interpret before comparing

Establish four layers:

1. **Task design:** what inputs the system receives, what work it performs, which tools or environment it can use, time and retry limits, human involvement, dataset split and what the grader observes.
2. **Score semantics:** metric name, unit, direction, aggregation, denominator, uncertainty and failure rule. Distinguish pass rate, accuracy, win rate, Elo-style rating, judge score, cost and latency. Never rewrite an Elo rating or comparison score as an accuracy percentage.
3. **System configuration:** exact model or system version, effort, tools, scaffolding, prompt or policy, safeguards, retries and fallback routing. A routed or agentic system result is not automatically a base-model result.
4. **Evidence relationship:** who ran the evaluation, who owns the benchmark, what artefact is available, and whether an independent party reproduced it.

For stateful automation benchmarks, determine whether grading checks the final simulated environment. A run that is semantically close may still fail strict state assertions. For human-judged deliverables, explain the comparison protocol, judge population and rating method before interpreting the number.

## Comparison gate

Call results directly comparable only when benchmark version, task split, scoring protocol, system allowances and reporting unit align. If any differ, present the numbers as contextual, not a ranking. Separate documented fact, calculation, inference and recommendation.

## Output

Give the reader:

- a one-sentence verdict on whether the claim is supported;
- a compact claim and evidence table;
- a plain-language description of the evaluated work;
- score semantics and the easiest likely misreading;
- the actual evaluated system configuration, including fallback routing;
- material limitations, conflicts and unknowns;
- the practical implication for the user's workflow.

For multiple claims, record them in the format described by [references/claim-register.md](references/claim-register.md). Run `python3 scripts/validate_claim_register.py REGISTER.json` to catch missing provenance and interpretation fields. The validator checks record completeness, not whether a source is truthful or a conclusion is sound.
