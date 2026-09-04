---
name: decision-research
description: Turn policy, programme, funding, market or strategy evidence into an auditable decision brief with source, claim, programme and contradiction registers. Use when research must reconcile money, constrain causal claims, expose uncertainty and support a consequential recommendation.
---

# Decision Research

Produce a defensible decision, not a fluent topic summary.

## Frame the decision

Before broad research, write:

- decision and decision owner;
- intended use and deadline;
- population, geography, period and definitions;
- options, counterfactual and constraints;
- critical claims that could change the decision;
- acceptance criteria and stopping rules.

## Build the case files

Copy the CSV templates from `assets/` into a case directory. Read [references/register-schemas.md](references/register-schemas.md) before editing them.

Keep four records:

1. evidence ledger, one row per source lineage;
2. claim register, one row per atomic proposition;
3. programme inventory, one row per financial amount and exact meaning;
4. contradiction register, one row per unresolved disagreement.

## Apply evidence discipline

- Use [references/source-hierarchy.md](references/source-hierarchy.md) and prefer the source that owns the claim.
- For public money, use [references/government-finance.md](references/government-finance.md). Match status, period, currency, fund source and scope before adding figures.
- For impact claims, use [references/causal-evidence.md](references/causal-evidence.md). Make the verb no stronger than the design.
- Register contradictions when found. Do not resolve them rhetorically.
- Treat search results and AI summaries as discovery aids, not evidence.
- Use code or a spreadsheet for material calculations and preserve reproducible inputs.

## Write and independently verify

Draft from the registers, using stable source IDs at the point of claim. Separate verified fact, source claim, inference, uncertainty and recommendation.

Before delivery, independently check every critical claim for citation entailment, scope, date, denominator, units, source lineage, competing evidence and causal wording. Recalculate material figures. A critical failure cannot be averaged away by strengths elsewhere.

Stop when critical criteria pass, open contradictions are disclosed and the recommendation remains stable under stated sensitivity assumptions. If evidence cannot close a critical criterion, label the conclusion blocked or qualify it.
