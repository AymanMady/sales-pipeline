# Data lineage

Lineage answers two questions: *where does this number come from?* (upstream)
and *what breaks if I change this table?* (downstream).

## Levels

- **Table level**: which tables are read to build a table. dbt provides it for
  free from `ref()` and `source()` (`dbt docs generate` draws the graph).
- **Column level**: which source columns feed a column. Needed for PII
  tracking and impact analysis of renames.

## Practical sources of lineage

- dbt manifest (`target/manifest.json`).
- OpenLineage events emitted by Airflow and Spark integrations.
- Query logs of the warehouse.

## Using it

Before dropping or renaming a column, list the downstream models and
dashboards, then change them in the same pull request or deprecate the column
for one release first.
