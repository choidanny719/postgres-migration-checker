import json

import pytest

from pgcheck.cli import main


@pytest.fixture
def scenario(tmp_path, pytestconfig):
    def perform(migration, *, query="SELECT id, name FROM items ORDER BY id", seed=True, extra=()):
        def write(name, content):
            p = tmp_path / name
            p.write_text(content)
            return str(p)
        args = ["--engine", pytestconfig.getoption("--database-engine"), "--baseline", write("schema.sql", "CREATE TABLE items (id integer PRIMARY KEY, name text)")]
        if seed:
            args += ["--seed", write("seed.sql", "INSERT INTO items VALUES (1, 'book')")]
        for i, m in enumerate([migration, *extra]):
            args += ["--migration", write(f"change{i}.sql", m)]
        return main([*args, "--query", write("query.sql", query), "--format", "json"])
    return perform


@pytest.mark.parametrize(("sql", "exit_code", "stage"), [
    ("ALTER TABLE items ADD COLUMN price integer", 0, "complete"),
    ("ALTER TABLE items RENAME name TO title", 1, "migrated query"),
    ("UPDATE items SET name = upper(name)", 1, "migrated query"),
    ("ALTER TABLE missing ADD price int", 1, "migration"),
    ("ALTER TABLE items ADD COLUMN price integer NOT NULL", 1, "migration"),
])
def test_migration(scenario, capsys, sql, exit_code, stage):
    assert scenario(sql) == exit_code
    assert json.loads(capsys.readouterr().out)["stage"].startswith(stage)


def test_broken_baseline_query(scenario, capsys):
    assert scenario("SELECT 1", query="SELECT total FROM items") == 2
    assert "baseline query" in json.loads(capsys.readouterr().out)["stage"]


def test_query_cannot_write(scenario, capsys):
    assert scenario("SELECT 1", query="DELETE FROM items") == 2
    assert "read-only" in json.loads(capsys.readouterr().out)["detail"]


def test_ordered_migrations(scenario):
    assert scenario("ALTER TABLE items ADD amount int", seed=False,
                    extra=["ALTER TABLE items RENAME amount TO price"]) == 0


def test_null_and_empty_string_are_distinct(scenario):
    assert scenario("UPDATE items SET name = ''", query="SELECT nullif(name, 'book') AS title FROM items") == 1


def test_failed_seed_is_a_setup_error(tmp_path, pytestconfig, capsys):
    schema, seed, query = (tmp_path / name for name in ["schema", "seed", "query"])
    schema.write_text("CREATE TABLE records(id integer PRIMARY KEY)")
    seed.write_text("INSERT INTO records VALUES (1), (1)")
    query.write_text("SELECT id FROM records")
    assert main(["--engine", pytestconfig.getoption("--database-engine"), "--baseline", str(schema), "--seed", str(seed),
                 "--migration", str(query), "--query", str(query)]) == 2
    assert capsys.readouterr().out.startswith("seed:")
