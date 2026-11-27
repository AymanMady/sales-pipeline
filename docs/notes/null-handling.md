# Null handling

## Three-valued logic

`NULL = NULL` is not true, and `WHERE status <> 'cancelled'` drops rows where
`status` is `NULL`. Use `IS DISTINCT FROM` when nulls must compare.

## Aggregates

`count(*)` counts rows, `count(col)` counts non-null values, and `avg` ignores
nulls. Decide whether missing means zero before aggregating.

## Joins

Nulls never match in a join key. Rows with a null foreign key disappear in an
inner join; use a left join and an "unknown" dimension member.

## Make intent explicit

Replace nulls deliberately with `coalesce` in staging, and document which
columns may legitimately be null.
