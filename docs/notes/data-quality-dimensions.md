# Data quality dimensions

| Dimension | Question | Example test |
|---|---|---|
| Completeness | are values present? | `not_null` on required columns |
| Uniqueness | one row per key? | `unique` on the primary key |
| Validity | values in the allowed domain? | `accepted_values`, ranges |
| Consistency | do related tables agree? | `relationships`, totals match |
| Timeliness | is the data fresh? | max(loaded_at) within SLA |
| Accuracy | does it match reality? | reconciliation with the source |

## Severity

Not every failure should stop the pipeline. Classify tests as **error** (block
publication) or **warn** (report, keep going).

## Quarantine

Route invalid rows to a quarantine table with the failure reason instead of
dropping them silently, and alert when their share exceeds a threshold.
