# PostgreSQL Migration Checker

A Python command-line tool that checks whether an application's SQL queries still work after a database change. It runs the queries before and after the change in a temporary PostgreSQL database and compares the results.

## How it works

Suppose a book catalog runs this query:

```sql
SELECT id, title FROM books ORDER BY id;
```

PostgreSQL can apply all three migrations below. The checker shows which ones affect the application.

| Migration | What happens to the existing query? | Result |
| --- | --- | --- |
| Add an optional `isbn` column | It returns the same IDs and titles. | Pass |
| Rename `title` to `book_title` | It fails because `title` no longer exists. | Fail |
| Convert every title to uppercase | It runs, but the titles it returns have changed. | Fail |

## Run locally

Requires Python 3.10 or newer and Docker. Start Docker, then run these commands from the repository root:

```bash
python -m pip install ".[test]"
cd examples/catalog
pg-migration-check --baseline baseline.sql --seed seed.sql --migration add-isbn.sql --query client-query.sql
```

Expected output:

```text
complete: 1 migration(s), 1 matching query result(s)
```

To see a failure, replace `add-isbn.sql` with `rename-title.sql` in the same command. The checker reports which query failed and includes PostgreSQL's error message.

## Check your own migration

| Argument | File to supply |
| --- | --- |
| `--baseline` | SQL that creates the current schema |
| `--seed` | Optional sample rows for the queries to read |
| `--migration` | SQL for the proposed change. Repeat for multiple migrations, in order. |
| `--query` | A query the application already uses. Repeat to check more queries. |

Use representative sample rows and an explicit `ORDER BY` when a query returns multiple rows. The checker compares column names, row order and values, including the difference between `NULL` and an empty string.

## Tests

From the repository root:

```bash
python -m pytest -q --database-engine docker
```

GitHub Actions runs the suite against native PostgreSQL and repeats the integration cases in Docker.

<details>
<summary>Database setup, report format and exit codes</summary>

Docker mode starts a fresh PostgreSQL 16 container and removes it and its volumes after the check. To use a local PostgreSQL installation, add `--engine native`. This mode creates a temporary cluster and requires a non-root user on Linux or macOS with `initdb`, `pg_ctl` and `psql` on the command path.

Use trusted SQL files. Each file runs in its own session, and the checker runs application queries in read-only transactions. The comparison holds results in memory and covers the data and queries you supply. Production lock times, concurrent writes and rollback safety require separate testing.

Use `--format json` to get the exit code, stage and result details.

| Exit code | Meaning |
| --- | --- |
| 0 | All migrations ran and the query results matched |
| 1 | A migration failed or an existing query failed or returned different data |
| 2 | The checker could not load the inputs, start the database or run the baseline |

</details>
