import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .engine import EngineError, native_database
from .rehearsal import Result, read_script, rehearse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Rehearse migrations on a disposable PostgreSQL cluster")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--seed", type=Path)
    parser.add_argument("--migration", required=True, action="append", type=Path)
    parser.add_argument("--query", required=True, action="append", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)
    try:
        baseline = read_script(args.baseline)
        seed = read_script(args.seed) if args.seed else None
        migrations = [(str(p), read_script(p)) for p in args.migration]
        queries = [(str(p), read_script(p)) for p in args.query]
        with native_database() as db:
            result = rehearse(db, baseline, seed, migrations, queries)
    except (OSError, ValueError, EngineError) as exc:
        result = Result(2, "setup", str(exc))
    if args.format == "json":
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"{result.stage}: {result.detail}")
    return result.code


if __name__ == "__main__":
    sys.exit(main())
