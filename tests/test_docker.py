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
    launch, start, ready, query, cleanup = command.call_args_list
    args = launch.args[0]
    name = args[args.index("--name") + 1]
    assert args[args.index("--network") + 1] == "none"
    assert start.args[0] == ["docker", "start", name]
    assert name in ready.args[0] and name in query.args[0]
    assert b"BEGIN READ ONLY;" in query.kwargs["data"]
    assert cleanup.args[0] == ["docker", "rm", "--force", "--volumes", name]


def test_missing_docker(monkeypatch):
    monkeypatch.setattr(engine.shutil, "which", lambda _: None)
    with pytest.raises(engine.EngineError, match="Docker is unavailable"):
        with engine.docker_database():
            pytest.fail("unexpected running container")


def test_failed_start_removes_container_and_volume(monkeypatch):
    command = Mock(side_effect=[b"container", engine.EngineError("failed start"), b"removed"])
    monkeypatch.setattr(engine.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(engine, "run", command)
    with pytest.raises(engine.EngineError, match="failed start"):
        with engine.docker_database():
            pytest.fail("unexpected running container")
    assert command.call_args.args[0][:4] == ["docker", "rm", "--force", "--volumes"]
