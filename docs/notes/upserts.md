# Upserts

## PostgreSQL

```sql
INSERT INTO dim_customer (customer_id, email, updated_at)
VALUES (%s, %s, %s)
ON CONFLICT (customer_id) DO UPDATE
SET email = EXCLUDED.email,
    updated_at = EXCLUDED.updated_at
WHERE dim_customer.updated_at < EXCLUDED.updated_at;
```

- Requires a unique index or constraint on the conflict columns.
- The `WHERE` clause prevents an older record from overwriting a newer one.

## MERGE

`MERGE INTO target USING source ON ... WHEN MATCHED THEN UPDATE WHEN NOT MATCHED
THEN INSERT` is available in PostgreSQL 15+, Delta Lake, Snowflake and
BigQuery. It also supports `WHEN MATCHED AND ... THEN DELETE`.

## Bulk upserts

For large batches, load into a temporary staging table with `COPY`, then run a
single `INSERT ... SELECT ... ON CONFLICT` from it. Row-by-row upserts from
Python are orders of magnitude slower.

## Duplicates in the batch

`ON CONFLICT` fails if the **same key appears twice in one statement**.
Deduplicate the batch first (keep the latest row per key).
