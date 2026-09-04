# Register schemas

Use UTF-8 CSV and stable IDs that are never reused.

## Evidence ledger

`source_id,title,publisher,url,published_date,accessed_date,source_type,source_tier,archive_path,notes`

## Claim register

`claim_id,claim_text,claim_type,materiality,status,source_ids,confidence,amount,currency,fiscal_period,amount_status,causal_strength,notes`

Financial fields are required together. Relationship fields use semicolon-separated IDs.

## Programme inventory

`programme_id,programme_name,agency,target_population,parent_programme_id,amount,currency,price_basis,fiscal_period,amount_status,fund_source,gross_or_net,one_time_or_ongoing,scope,include_in_reconciled_total,overlap_group,source_ids,source_location,notes`

## Contradiction register

`contradiction_id,topic,claim_ids,source_ids,conflict_type,description,decision_impact,status,resolution,owner,updated_date`

Allowed contradiction states are `open`, `resolved`, `accepted_uncertainty` and `superseded`.
