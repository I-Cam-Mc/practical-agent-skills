---
name: rekordbox-transition-miner
description: Turn Rekordbox-compatible DJ history into read-only transition candidates and human-confirmed mix recipes. Use when analysing set history or building a transition notebook, not when modifying DJ libraries or claiming that adjacent tracks prove a successful mix.
---

# Rekordbox Transition Miner

Build an evidence-backed transition notebook from DJ history while preserving the source library.

## Preserve the evidence boundary

- Treat history as observed play order only. It does not prove that a transition occurred, sounded good, or used a particular technique.
- Keep Rekordbox, Lexicon, Serato and audio files read-only unless the user separately approves a write.
- Prefer a normal export or a read-only snapshot from a library manager. Do not bypass database encryption or application protections.
- Never upload library data, file paths or listening history without explicit approval.
- Remove personal paths and event names from shared outputs.

## Build the notebook

1. Inventory the available history source, its version, date range and fields.
2. Copy or export the smallest useful read-only snapshot before analysis.
3. Normalise sessions and ordered plays using the model in [references/data-model.md](references/data-model.md).
4. Resolve track identity conservatively: stable source ID first, exact file location second, then normalised title, artist and duration. Put uncertain matches in a review queue.
5. Generate directional adjacent pairs. Keep `A -> B` distinct from `B -> A`.
6. Rank candidates using evidence such as repeat count and number of distinct sessions. Do not label them good or proven.
7. Ask the DJ to confirm, reject or defer candidates. Confirmation is the only route to a confirmed recipe.
8. Capture timing and technique manually. Store both seconds and beat/bar references when available.

Use the synthetic files in `assets/` as format examples only. Adapt field names to the actual export rather than assuming a proprietary schema is stable.

## Report honestly

Return:

- source snapshot and read-only status;
- session, play and candidate counts;
- identity resolution coverage and unresolved count;
- top review candidates with their evidence;
- confirmed recipes separately from candidates;
- limitations, especially missing playhead, fader, EQ, recording or crowd-response data.

Do not infer exact historic transition timestamps from play order. Later timing suggestions may use cue points, tempo, key, beat grids and structure, but remain suggestions until confirmed by a person.
