import argparse, json, sys
from linkguard.training import train_model, TrainingDataError


def main(argv=None):
    p = argparse.ArgumentParser(description="LinkGuard 재구성본 Random Forest 학습")
    p.add_argument("--csv", required=True)
    p.add_argument("--output", default="artifacts/linkguard.joblib")
    p.add_argument("--report", default="artifacts/metrics.json")
    p.add_argument("--cv-folds", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--trees", type=int, default=200)
    p.add_argument("--model-version")
    a = p.parse_args(argv)
    try:
        r = train_model(
            a.csv,
            a.output,
            a.report,
            cv_folds=a.cv_folds,
            seed=a.seed,
            test_size=a.test_size,
            trees=a.trees,
            model_version=a.model_version,
        )
    except (TrainingDataError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps(r["holdout"], ensure_ascii=False))
    print("입력 데이터의 독립 평가 결과이며 실제 운영 성능을 보장하지 않습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
