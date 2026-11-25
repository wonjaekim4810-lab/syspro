"""Local operator CLI. No HTTP upload/activation endpoint is exposed."""

import argparse, json, sys
from dataclasses import asdict
from pathlib import Path
from linkguard.adapters import build_adapter
from linkguard.registry import SQLiteRegistry


def main(argv=None):
    p = argparse.ArgumentParser(description="학습 모델 DB 등록/교체 도구")
    p.add_argument("--db", default="registry/models.sqlite3")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("list")
    register = commands.add_parser("register")
    register.add_argument("--name", required=True)
    register.add_argument("--version", required=True)
    register.add_argument("--backend", choices=["joblib", "onnx", "custom"], required=True)
    register.add_argument("--artifact", required=True, type=Path)
    register.add_argument("--input-kind", choices=["features40", "url_text"], default="features40")
    register.add_argument("--positive-index", type=int, choices=[0, 1], default=1)
    register.add_argument("--activate", action="store_true")
    active = commands.add_parser("activate")
    active.add_argument("--id", required=True, type=int)
    args = p.parse_args(argv)
    db = SQLiteRegistry(args.db)
    try:
        if args.command == "init":
            db.initialize()
            result = {"status": "initialized"}
        elif args.command == "list":
            result = [asdict(x) for x in db.list_models()]
        elif args.command == "activate":
            result = asdict(db.activate(args.id, build_adapter))
        else:
            record = db.register(
                name=args.name,
                version=args.version,
                backend=args.backend,
                artifact_path=args.artifact,
                input_kind=args.input_kind,
                positive_class_index=args.positive_index,
            )
            if args.activate:
                record = db.activate(record.id, build_adapter)
            result = asdict(record)
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
