import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path


class EngineError(RuntimeError):
    pass


def run(args, *, data=None, env=None, timeout=45):
    try:
        result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EngineError(str(exc)) from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).decode(errors="replace").strip()
        raise EngineError(detail[-2500:] or f"{args[0]} exited with {result.returncode}")
    return result.stdout


class Database:
    def __init__(self, command, env=None):
        self.command = command
        self.env = env

    def execute(self, sql, *, readonly=False):
        script = "BEGIN READ ONLY;\n" + sql + "\n;\nROLLBACK;\n" if readonly else sql
        return run([*self.command, "-X", "-q", "--csv", "-v", "ON_ERROR_STOP=1", "-f", "-"],
                   data=script.encode(), env=self.env)


@contextmanager
def native_database():
    commands = {name: shutil.which(name) for name in ("initdb", "pg_ctl", "psql")}
    if not all(commands.values()):
        raise EngineError("native mode needs initdb, pg_ctl and psql on PATH")
    env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
    env.update(PGCLIENTENCODING="UTF8", LC_ALL="C")
    with tempfile.TemporaryDirectory(prefix="pgcheck-") as tmp:
        data = str(Path(tmp) / "data")
        run([commands["initdb"], "-D", data, "-U", "rehearsal", "--auth-local=trust",
             "--auth-host=reject", "--no-locale", "--encoding=UTF8"], env=env)
        auto_conf = Path(data) / "postgresql.auto.conf"
        socket = tmp.replace("'", "''").replace("\\", "\\\\")
        with auto_conf.open("a") as config:
            config.write(f"\nlisten_addresses = ''\nunix_socket_directories = '{socket}'\nport = 5432\n")
        ctl = [commands["pg_ctl"], "-D", data, "-w", "-t", "30"]
        try:
            log = Path(tmp) / "server.log"
            try:
                run([*ctl, "-l", str(log), "start"], env=env)
            except EngineError as exc:
                detail = log.read_text(errors="replace")[-2000:] if log.exists() else ""
                raise EngineError(f"{exc}\n{detail}".strip()) from exc
            yield Database([commands["psql"], "-h", tmp, "-p", "5432", "-U", "rehearsal",
                            "-d", "postgres"], env)
        finally:
            if (Path(data) / "postmaster.pid").exists():
                run([*ctl, "-m", "immediate", "stop"], env=env)
