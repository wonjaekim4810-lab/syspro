import argparse, json, sys
from pathlib import Path
from linkguard.features import FeatureExtractor, FEATURE_SCHEMA_VERSION
from linkguard.urltools import normalize_url


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("features")
    a.add_argument("url")
    a = sub.add_parser("predict")
    a.add_argument("url")
    selection = a.add_mutually_exclusive_group()
    selection.add_argument(
        "--model", type=Path, help="Legacy Random Forest artifact, bypassing registry"
    )
    selection.add_argument(
        "--db", type=Path, help="SQLite model registry (default: registry/models.sqlite3)"
    )
    a = p.parse_args(argv)
    try:
        url = normalize_url(a.url)
        if a.command == "features":
            e = FeatureExtractor()
            result = {
                "url": url,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "features": e.extract(url),
                "observations": e.explain(url),
                "notice": "특징 관찰이며 피싱 판정이나 모델 기여도 설명이 아닙니다.",
            }
        else:
            from linkguard.model import URLDetector

            if a.model is not None:
                result = URLDetector.load(a.model).predict(url)
            else:
                from linkguard.registry import SQLiteRegistry
                from linkguard.registered_detector import RegisteredDetector

                result = RegisteredDetector(
                    SQLiteRegistry(a.db or "registry/models.sqlite3")
                ).predict(url)
    except (ValueError, RuntimeError, OSError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
