"""Pretrained model slots. Artifact loading is an operator-only trusted action."""

from __future__ import annotations
from io import BytesIO
import hashlib
import re
import warnings
from pathlib import Path
from typing import Protocol
import joblib
import numpy as np
import sklearn
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.utils.validation import check_is_fitted
from .features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT
from .model import ModelUnavailableError
from .registry import ModelRecord


class InferenceAdapter(Protocol):
    def probability(self, url: str, vector: list[float]) -> float: ...


def checked_artifact(record: ModelRecord) -> bytes:
    try:
        with Path(record.artifact_path).open("rb") as stream:
            data = stream.read(256 * 1024 * 1024 + 1)
        if (
            not data
            or len(data) > 256 * 1024 * 1024
            or hashlib.sha256(data).hexdigest() != record.sha256
        ):
            raise ValueError("artifact mismatch")
        return data
    except (OSError, ValueError) as error:
        raise ModelUnavailableError("등록된 모델 파일 또는 SHA-256을 확인하세요.") from error


def checked_vector(vector, dtype=np.float32):
    x = np.asarray(vector, dtype=dtype)
    if x.shape != (40,) or not np.isfinite(x).all():
        raise ModelUnavailableError("40개 수치 특징 입력이 필요합니다.")
    return x.reshape(1, 40)


def checked_probability(value):
    p = float(value)
    if not np.isfinite(p) or not 0 <= p <= 1:
        raise ModelUnavailableError("모델은 0~1의 피싱 클래스 출력을 반환해야 합니다.")
    return p


class JoblibAdapter:
    """Artifact containing a fitted estimator/Pipeline that accepts NumPy[1,40]."""

    def __init__(self, model):
        self.model = model

    @classmethod
    def load(cls, record):
        try:
            data = checked_artifact(record)
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                bundle = joblib.load(BytesIO(data))
            if (
                not isinstance(bundle, dict)
                or type(bundle.get("artifact_version")) is not int
                or bundle["artifact_version"] != 1
                or bundle.get("feature_names") != list(FEATURE_NAMES)
                or bundle.get("feature_schema_version") != FEATURE_SCHEMA_VERSION
                or bundle.get("resource_fingerprint") != RESOURCE_FINGERPRINT
            ):
                raise ValueError("input schema mismatch")
            if (
                bundle.get("metadata", {}).get("sklearn_version") != sklearn.__version__
                or bundle.get("model_version") != record.version
            ):
                raise ValueError("model version mismatch")
            if record.positive_class_index != 1:
                raise ValueError("classes [0,1] required")
            model = bundle["model"]
            check_is_fitted(model)
            if (
                not callable(getattr(model, "predict_proba", None))
                or getattr(model, "n_features_in_", None) != 40
                or list(model.classes_) != [0, 1]
            ):
                raise ValueError("binary predict_proba estimator required")
            names = getattr(model, "feature_names_in_", None)
            if names is not None and list(names) != list(FEATURE_NAMES):
                raise ValueError("feature order")
            adapter = cls(model)
            adapter.probability("", [0.0] * 40)
            return adapter
        except Exception as error:
            raise ModelUnavailableError(
                "학습된 ML 모델의 버전·스키마·클래스 순서를 확인하세요."
            ) from error

    def probability(self, url, vector):
        # Keep float64 for sklearn; ONNX uses float32 explicitly.
        x = checked_vector(vector, dtype=np.float64)
        values = np.asarray(self.model.predict_proba(x), dtype=float)
        if (
            values.shape != (1, 2)
            or not np.isfinite(values).all()
            or (values < 0).any()
            or (values > 1).any()
            or not np.isclose(values.sum(), 1)
        ):
            raise ModelUnavailableError("ML 모델은 [정상, 피싱] 2개 클래스 출력을 반환해야 합니다.")
        return checked_probability(values[0, 1])


class OnnxFeatureAdapter:
    """Optional DL/ML ONNX slot: float32 [1,40] -> probability, never logits."""

    @classmethod
    def load(cls, record):
        try:
            import onnxruntime as ort
        except ImportError as error:
            raise ModelUnavailableError(
                "ONNX 모델을 쓰려면 requirements-onnx.txt를 설치하세요."
            ) from error
        try:
            adapter = cls()
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            adapter.session = ort.InferenceSession(
                checked_artifact(record), sess_options=options, providers=["CPUExecutionProvider"]
            )
            inputs = adapter.session.get_inputs()
            if (
                len(inputs) != 1
                or inputs[0].type != "tensor(float)"
                or len(inputs[0].shape) != 2
                or inputs[0].shape[-1] != 40
            ):
                raise ValueError("expected float32 [batch,40]")
            outputs = adapter.session.get_outputs()
            if len(outputs) != 1 or outputs[0].type not in {"tensor(float)", "tensor(double)"}:
                raise ValueError("one probability tensor output required")
            adapter.input_name = inputs[0].name
            adapter.positive_index = record.positive_class_index
            adapter.probability("", [0.0] * 40)
            return adapter
        except Exception as error:
            raise ModelUnavailableError(
                "ONNX 모델의 40개 특징 입력과 확률 출력 형식을 확인하세요."
            ) from error

    def probability(self, url, vector):
        raw = np.asarray(self.session.run(None, {self.input_name: checked_vector(vector)})[0])
        if raw.dtype.kind != "f":
            raise ModelUnavailableError(
                "ONNX 출력은 클래스 라벨이 아닌 부동소수 확률이어야 합니다."
            )
        values = raw.astype(float, copy=False)
        if values.shape == (1, 2):
            if (
                not np.isfinite(values).all()
                or (values < 0).any()
                or (values > 1).any()
                or not np.isclose(values.sum(), 1)
            ):
                raise ModelUnavailableError("ONNX softmax 출력 범위 오류")
            return checked_probability(values[0, self.positive_index])
        if values.shape in {(1,), (1, 1)}:
            return checked_probability(values.reshape(-1)[0])
        raise ModelUnavailableError("ONNX 출력은 [1,2], [1,1] 또는 [1]이어야 합니다.")


class CustomURLTextAdapter:
    """User extension point for tokenizer/CNN/RNN/Transformer/raw-URL models.

    Implement load() and probability() after attaching your tokenizer, input shape,
    trained weights and preprocessing version. No fake default inference is supplied.
    """

    @classmethod
    def load(cls, record):
        checked_artifact(record)
        raise ModelUnavailableError(
            "사용자 정의 DL 어댑터 자리를 실제 학습 코드·토크나이저로 구현해야 합니다."
        )

    def probability(self, url, vector):
        raise ModelUnavailableError("사용자 정의 추론 함수를 구현하세요.")


def build_adapter(record: ModelRecord) -> InferenceAdapter:
    if not isinstance(record.version, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", record.version
    ):
        raise ModelUnavailableError("등록 모델 버전 형식이 올바르지 않습니다.")
    if type(record.positive_class_index) is not int or record.positive_class_index not in (0, 1):
        raise ModelUnavailableError("양성 클래스 인덱스를 확인하세요.")
    if not isinstance(record.sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", record.sha256):
        raise ModelUnavailableError("모델 파일 지문을 확인하세요.")
    if record.backend in {"joblib", "onnx"}:
        if (
            record.input_kind != "features40"
            or record.feature_schema_version != FEATURE_SCHEMA_VERSION
            or record.resource_fingerprint != RESOURCE_FINGERPRINT
        ):
            raise ModelUnavailableError(
                "등록 모델의 입력 스키마/사전 지문이 현재 40개 특징과 다릅니다."
            )
        return (
            JoblibAdapter.load(record)
            if record.backend == "joblib"
            else OnnxFeatureAdapter.load(record)
        )
    if record.backend == "custom" and record.input_kind == "url_text":
        return CustomURLTextAdapter.load(record)
    raise ModelUnavailableError("지원되는 모델 어댑터가 없습니다.")
