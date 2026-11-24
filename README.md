# PostgreSQL Migration Checker

Rehearse SQL migrations on a disposable PostgreSQL database. The checker creates the old schema, loads sample data and records the output of existing application queries. It applies the proposed migrations, reruns those queries and reports the first SQL error or changed result.

## Try it

Install Python 3.10+ and start Docker, then run from the repository root:

```sh
python -m pip install '.[test]'
cd examples/catalog
pg-migration-check --baseline baseline.sql --seed seed.sql --migration add-isbn.sql --query client-query.sql
pg-migration-check --baseline baseline.sql --seed seed.sql --migration rename-title.sql --query client-query.sql
```

Adding an optional ISBN passes. Renaming the title column succeeds in PostgreSQL but breaks the old client query. Try `change-data.sql` to see a migration that preserves the columns and changes their values.

| Exit | Meaning |
| --- | --- |
| 0 | All migrations applied and all checked query results matched |
| 1 | A migration failed, or a previously working query failed or returned different output |
| 2 | Invalid input, setup failure or an unusable baseline |

Add `--format json` for a report containing the exit code, stage and detail. Repeat `--migration` to apply files in the supplied order, and repeat `--query` for multiple client queries. The seed is optional.

## Execution

Docker mode starts a fresh `postgres:16` container with no network or published port. The checker uses the container's Unix socket and removes the container and its anonymous volumes after the run. Native mode (`--engine native`) creates a temporary cluster with its own socket. It requires `initdb`, `pg_ctl` and `psql` on PATH and a non-root user on Linux or macOS.

Supply trusted SQL and small, representative fixtures. Each file runs in a separate psql session; put transaction boundaries in migration files as needed. Query files run in read-only transactions. Comparison includes column labels, row order, NULLs and values; use an explicit `ORDER BY` and deterministic queries. Results are compared in memory. The check covers the supplied data and queries; it does not simulate concurrent writes, production lock durations or a rollback.

## Tests

From the repository root, run `python -m pytest -q --database-engine docker` or use the native PostgreSQL binaries and run `python -m pytest -q`. GitHub Actions exercises both modes.
