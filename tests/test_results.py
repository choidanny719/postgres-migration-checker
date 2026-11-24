import pytest

from pgcheck.engine import EngineError
from pgcheck.rehearsal import rehearse


class ScriptedDatabase:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []

    def execute(self, sql, *, readonly=False):
        self.calls.append((sql, readonly))
        if sql == self.failure:
            raise EngineError("failed statement")
        return b"id\n1\n"


@pytest.mark.parametrize(("fault", "code", "stage"), [
    ("schema", 2, "baseline"), ("seed", 2, "seed"), ("query", 2, "baseline query q"),
    ("change", 1, "migration m"), (None, 0, "complete")
])
def test_stages(fault, code, stage):
    db = ScriptedDatabase(fault)
    result = rehearse(db, "schema", "seed", [("m", "change")], [("q", "query")])
    assert (result.code, result.stage) == (code, stage)
    if not fault:
        assert db.calls == [("schema", False), ("seed", False), ("query", True),
                            ("change", False), ("query", True)]
