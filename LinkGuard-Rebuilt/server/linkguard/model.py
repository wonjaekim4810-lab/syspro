"""Trusted local joblib loading only: pickle is not a sandbox for uploads."""

from pathlib import Path
import re, warnings
import joblib, numpy as np, sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.utils.validation import check_is_fitted
from .features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT, FeatureExtractor
from .urltools import normalize_url


class ModelUnavailableError(RuntimeError):
    pass


class URLDetector:
    def __init__(self, model, version):
        self.model = model
        self.model_version = version
        self.extractor = FeatureExtractor()

    @classmethod
    def load(cls, path):
        try:
            p = Path(path)
            if not p.is_file() or not 0 < p.stat().st_size <= 256 * 1024 * 1024:
                raise ValueError()
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                a = joblib.load(p)
            if (
                not isinstance(a, dict)
                or type(a.get("artifact_version")) != int
                or a["artifact_version"] != 1
            ):
                raise ValueError()
            if (
                a.get("feature_names") != list(FEATURE_NAMES)
                or a.get("feature_schema_version") != FEATURE_SCHEMA_VERSION
                or a.get("resource_fingerprint") != RESOURCE_FINGERPRINT
            ):
                raise ValueError()
            if (
                a.get("thresholds") != {"caution": 40, "danger": 80}
                or a.get("metadata", {}).get("sklearn_version") != sklearn.__version__
            ):
                raise ValueError()
            version = a.get("model_version")
            if not isinstance(version, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", version
            ):
                raise ValueError()
            m = a.get("model")
            if not isinstance(m, RandomForestClassifier):
                raise ValueError()
            check_is_fitted(m)
            if (
                m.n_features_in_ != len(FEATURE_NAMES)
                or m.n_outputs_ != 1
                or list(m.classes_) != [0, 1]
                or not m.estimators_
            ):
                raise ValueError()
            detector = cls(m, version)
            detector._probability([0.0] * len(FEATURE_NAMES))
            return detector
        except Exception as e:
            raise ModelUnavailableError("학습된 분석 모델을 사용할 수 없습니다.") from e

    def _probability(self, vector):
        x = np.asarray(vector, dtype=float)
        if x.shape != (len(FEATURE_NAMES),) or not np.isfinite(x).all():
            raise ModelUnavailableError("특징 벡터 오류")
        p = np.asarray(self.model.predict_proba(x.reshape(1, -1)), dtype=float)
        if (
            p.shape != (1, 2)
            or not np.isfinite(p).all()
            or (p < 0).any()
            or (p > 1).any()
            or not np.isclose(p.sum(), 1)
        ):
            raise ModelUnavailableError("모델 출력 오류")
        return float(p[0, 1])

    def predict(self, url):
        normalized = normalize_url(url)
        try:
            score = max(
                0, min(100, round(self._probability(self.extractor.vector(normalized)) * 100))
            )
            reasons = []
            for r in self.extractor.explain(normalized):
                if not isinstance(r, str):
                    raise ValueError()
                r = " ".join(r.split())[:500]
                if r and r not in reasons:
                    reasons.append(r)
            return {
                "url": normalized,
                "status": "danger" if score >= 80 else "caution" if score >= 40 else "safe",
                "score": score,
                "reasons": reasons[:11] + ["관찰된 URL 특징이며 모델의 기여도 설명이 아닙니다."],
                "model_version": self.model_version,
            }
        except Exception as e:
            raise ModelUnavailableError("모델 예측에 실패했습니다.") from e
