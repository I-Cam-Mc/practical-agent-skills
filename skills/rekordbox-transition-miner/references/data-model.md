# Transition notebook data model

Keep source evidence separate from human judgement.

## Source tables

### Track

- `track_id`: stable local notebook identifier
- `source_system`, `source_track_id`
- `title`, `artist`, `duration_seconds`
- `location_hash`: optional local hash, not a public path
- `identity_status`: `resolved`, `ambiguous`, `unresolved`

### Session

- `session_id`, `source_session_id`
- `started_at`, `name`
- `source_snapshot_id`

### History entry

- `session_id`, `position`, `track_id`
- source metadata needed to reproduce the match

## Derived evidence

### Candidate

- `outgoing_track_id`, `incoming_track_id`
- `appearance_count`, `distinct_session_count`
- `evidence_session_ids`
- `review_status`: `unreviewed`, `confirmed`, `rejected`, `deferred`

### Confirmed recipe

- directional outgoing and incoming track IDs
- outgoing and incoming marker times in seconds
- optional beat and bar references
- blend length in bars
- transition style and technique notes
- context, rating and confidence
- confirmation date and human confirmer
- supporting session IDs

Never derive confirmation from `appearance_count`.
