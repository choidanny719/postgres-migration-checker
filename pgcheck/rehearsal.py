from dataclasses import dataclass
from pathlib import Path

from .engine import EngineError


@dataclass(frozen=True)
class Result:
    code: int
    stage: str
    detail: str


def read_script(path):
    sql = Path(path).read_text(encoding="utf-8")
    if not sql.strip():
        raise ValueError(f"{path} is empty")
    return sql


def rehearse(db, baseline, seed, migrations, queries):
    stage, code = "baseline", 2
    try:
        db.execute(baseline)
        if seed is not None:
            stage = "seed"
            db.execute(seed)
        expected = []
        for name, query in queries:
            stage = f"baseline query {name}"
            expected.append(db.execute(query, readonly=True))
        code = 1
        for name, sql in migrations:
            stage = f"migration {name}"
            db.execute(sql)
        for (name, query), original in zip(queries, expected):
            stage = f"migrated query {name}"
            if db.execute(query, readonly=True) != original:
                return Result(1, stage, "query output changed (columns, rows, values or ordering)")
    except EngineError as exc:
        return Result(code, stage, str(exc))
    return Result(0, "complete", f"{len(migrations)} migration(s), {len(queries)} matching query result(s)")
