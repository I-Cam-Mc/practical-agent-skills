# Rekordbox Transition Miner

A Codex skill for turning DJ play history into reviewable transition candidates and confirmed mix recipes.

The workflow treats adjacent tracks as evidence that two songs were played in sequence, not proof that the transition worked. It keeps the source DJ library read-only and records human confirmation separately.

## Install

Install the skill from `skills/rekordbox-transition-miner` using your preferred Codex skill installer, or copy that folder into your Codex skills directory.

## What it produces

- a normalised history snapshot;
- directional transition candidates ranked by repeated evidence;
- an identity-resolution queue for uncertain tracks;
- confirmed recipes with timing, bars, style, context and notes;
- provenance linking every candidate or recipe to its source sessions.

No DJ library, playlist, cue point or audio file is modified unless a user separately requests and approves that work.

This is an independent community project. It is not affiliated with or endorsed by AlphaTheta, Pioneer DJ, Lexicon, Serato or their respective owners. Product names are used only to describe compatibility.

## Licence

MIT. See [LICENSE](LICENSE).
