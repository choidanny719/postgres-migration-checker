from unittest.mock import Mock

import pytest

from pgcheck import engine


def test_container_is_isolated_and_removed_on_error(monkeypatch):
    command = Mock(return_value=b"")
    monkeypatch.setattr(engine.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(engine, "run", command)
    with pytest.raises(RuntimeError, match="interrupted"):
        with engine.docker_database() as db:
            db.execute("SELECT 1", readonly=True)
            raise RuntimeError("interrupted")
    launch, ready, query, cleanup = command.call_args_list
    args = launch.args[0]
    name = args[args.index("--name") + 1]
    assert args[args.index("--network") + 1] == "none"
    assert name in ready.args[0] and name in query.args[0]
    assert b"BEGIN READ ONLY;" in query.kwargs["data"]
    assert cleanup.args[0] == ["docker", "rm", "--force", name]


def test_missing_docker(monkeypatch):
    monkeypatch.setattr(engine.shutil, "which", lambda _: None)
    with pytest.raises(engine.EngineError, match="Docker is unavailable"):
        with engine.docker_database():
            pytest.fail("unexpected running container")
