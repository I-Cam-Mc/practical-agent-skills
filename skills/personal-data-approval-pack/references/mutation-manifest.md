# Mutation manifest

Use JSON with one object per exact operation:

```json
{
  "manifest_version": 1,
  "destination": {
    "system": "example-contacts",
    "account_label": "Personal"
  },
  "observed_at": "2030-01-01T00:00:00Z",
  "operations": [
    {
      "operation_id": "OP-001",
      "action": "update",
      "target_id": "synthetic-record-1",
      "before": {"display_name": "Alex Example"},
      "after": {"display_name": "Alexandra Example"},
      "reason": "User-confirmed canonical name",
      "confidence": "confirmed"
    },
    {
      "operation_id": "OP-002",
      "action": "delete",
      "target_id": "synthetic-record-2",
      "before": {
        "display_name": "Duplicate Example",
        "email": "duplicate@example.invalid"
      },
      "after": null,
      "tombstone": {
        "expected_state": "absent",
        "backup_record_id": "backup:synthetic-record-2"
      },
      "reason": "Exact duplicate confirmed by the user",
      "confidence": "confirmed"
    },
    {
      "operation_id": "OP-003",
      "action": "merge",
      "survivor_id": "synthetic-record-3",
      "source_ids": ["synthetic-record-4"],
      "before": {
        "survivor": {
          "id": "synthetic-record-3",
          "display_name": "Casey Example"
        },
        "sources": [
          {
            "id": "synthetic-record-4",
            "display_name": "Casey Example",
            "email": "casey@example.invalid"
          }
        ]
      },
      "after": {
        "display_name": "Casey Example",
        "email": "casey@example.invalid"
      },
      "tombstones": [
        {
          "source_id": "synthetic-record-4",
          "expected_state": "absent",
          "backup_record_id": "backup:synthetic-record-4"
        }
      ],
      "reason": "Identity and survivor confirmed by the user",
      "confidence": "confirmed"
    }
  ]
}
```

Required rules:

- `action` must be exactly `update`, `delete` or `merge`; undefined actions are non-executable;
- use stable operation IDs and stable record IDs (`target_id`, `survivor_id` and
  `source_ids` as appropriate);
- include the exact destination;
- capture the observation time;
- an `update` requires `target_id` plus changed fields in `before` and `after`;
- a `delete` requires `target_id`, the exact relevant `before` state, `after: null` and a tombstone whose expected state is `absent` and whose backup record is named;
- a `merge` requires one `survivor_id`, one or more distinct `source_ids`, exact before-state records, the survivor's expected `after` fields and one absence tombstone per source ID;
- reject execution when the live before-state differs;
- reject a merge when a source ID equals the survivor ID or a source/tombstone set differs;
- do not store secrets or unnecessary private fields;
- approval covers only listed operation IDs.
