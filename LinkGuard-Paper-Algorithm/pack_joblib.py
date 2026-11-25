"""Wrap an externally trained, trusted estimator after verifying the input contract.

This verifies shape, not your training data's semantic column order. Train with
FeatureExtractor.vector() order, including all preprocessing inside the estimator.
"""

import argparse
from pathlib import Path
import re
import joblib
import sklearn
from sklearn.utils.validation import check_is_fitted
from linkguard.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT


def export_pretrained(model, output, version):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", version):
        raise ValueError("모델 버전 형식 오류")
    check_is_fitted(model)
    if (
        getattr(model, "n_features_in_", None) != 40
        or list(model.classes_) != [0, 1]
        or not callable(getattr(model, "predict_proba", None))
    ):
        raise ValueError("40개 특징, 클래스[0,1], predict_proba 모델이 필요합니다.")
    names = getattr(model, "feature_names_in_", None)
    if names is not None and list(names) != list(FEATURE_NAMES):
        raise ValueError("특징 열 순서가 다릅니다.")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "artifact_version": 1,
            "feature_names": list(FEATURE_NAMES),
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "resource_fingerprint": RESOURCE_FINGERPRINT,
            "model_version": version,
            "model": model,
            "thresholds": {"caution": 40, "danger": 80},
            "metadata": {"sklearn_version": sklearn.__version__, "origin": "external_training"},
        },
        output,
    )
    return output


def main(argv=None):
    p = argparse.ArgumentParser(
        description="직접 학습한 신뢰 가능한 joblib 모델을 LinkGuard 형식으로 포장"
    )
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--version", required=True)
    args = p.parse_args(argv)
    if Path(args.input).resolve() == Path(args.output).resolve():
        p.error("입력과 출력 파일은 달라야 합니다.")
    export_pretrained(joblib.load(args.input), args.output, args.version)
    print(
        "모델 포장 완료. modelctl.py register로 등록하세요. 학습 데이터의 특징 순서는 직접 확인해야 합니다."
    )


if __name__ == "__main__":
    main()
