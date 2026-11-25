"""DB selection and inference are separate from training and feature extraction."""

import threading
from .adapters import build_adapter, checked_probability
from .features import FeatureExtractor
from .model import ModelUnavailableError
from .registry import ModelRegistry
from .urltools import normalize_url


class RegisteredDetector:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.extractor = FeatureExtractor()
        self._record = None
        self._adapter = None
        self._lock = threading.RLock()

    def _selected(self):
        with self._lock:
            try:
                record = self.registry.get_active()
                if record is None:
                    raise ModelUnavailableError("활성 학습 모델이 없습니다.")
                if record != self._record:
                    # Never use a previously cached model when activation of another model fails.
                    self._record = None
                    self._adapter = None
                    adapter = build_adapter(record)
                    self._record = record
                    self._adapter = adapter
                return record, self._adapter
            except ModelUnavailableError:
                raise
            except Exception as error:
                raise ModelUnavailableError("모델 DB 또는 등록 메타데이터를 확인하세요.") from error

    def ready(self):
        try:
            self._selected()
            return True
        except ModelUnavailableError:
            return False

    def predict(self, url):
        normalized = normalize_url(url)
        record, adapter = self._selected()
        try:
            p = checked_probability(
                adapter.probability(normalized, self.extractor.vector(normalized))
            )
            score = max(0, min(100, round(p * 100)))
            reasons = []
            for reason in self.extractor.explain(normalized):
                clean = " ".join(reason.split())[:500]
                if clean and clean not in reasons:
                    reasons.append(clean)
            return {
                "url": normalized,
                "status": "danger" if score >= 80 else "caution" if score >= 40 else "safe",
                "score": score,
                "reasons": reasons[:11] + ["관찰된 URL 특징이며 모델의 기여도 설명이 아닙니다."],
                "model_version": record.version,
            }
        except Exception as error:
            raise ModelUnavailableError("등록 모델 추론을 완료하지 못했습니다.") from error
