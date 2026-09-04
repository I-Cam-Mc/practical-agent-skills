# Claim register

Use a claim register when checking several results or when a conclusion may be revisited later. Store concise paraphrases and links, not copied evaluation prompts or reports.

## Shape

The example below is synthetic and passes the bundled validator. Replace its
claim, sources and access date with current evidence. Do not treat the example
domain or values as a real benchmark result.

```json
{
  "register_version": 1,
  "claims": [
    {
      "id": "synthetic-result",
      "claim": "A synthetic system received 120 comparison-rating points",
      "benchmark": {
        "name": "Synthetic Deliverable Evaluation",
        "version": "v1",
        "task_design": "Systems produce bounded deliverables from synthetic briefs",
        "scoring_method": "Reviewers choose the stronger deliverable in blind pairs",
        "split": "public synthetic fixture"
      },
      "result": {
        "value": 120,
        "metric": "comparison rating",
        "unit": "rating points",
        "direction": "higher",
        "interpretation": "Relative preference under this pairing protocol",
        "not_equivalent_to": "120 percent accuracy"
      },
      "system": {
        "name": "Synthetic System",
        "model_version": "fixture-v1",
        "effort": "fixed synthetic setting",
        "tools": ["fixture editor"],
        "scaffolding": "documented synthetic harness",
        "fallback_routing": "none"
      },
      "evidence": [
        {
          "publisher_relationship": "benchmark-owner",
          "source_kind": "methodology",
          "url": "https://example.org/method",
          "published_at": "unknown",
          "accessed_at": "2026-09-05",
          "supports": "Synthetic task and scoring protocol"
        }
      ],
      "limitations": ["Synthetic fixture, not a real model claim"],
      "status": "provisional"
    }
  ]
}
```

## Interpretation rules

- `verified` means direct evidence supports the bounded wording, not that the model is generally superior.
- Use `provisional` for a vendor result without an adequate reproducible artefact or independent check.
- Use `conflicted` when credible sources disagree and explain why.
- Use `unverified` when the direct source or required configuration cannot be established.
- Record `unknown` rather than assuming default effort, tools, retries or fallback behaviour.
- Link to the result or methodology itself, not a search-results page.
- Keep access dates current. Old papers can remain valid, but current leaderboards and product labels still need a fresh read.
