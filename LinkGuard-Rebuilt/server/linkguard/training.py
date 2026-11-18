"""Rebuilt domain-disjoint training. Only trusted local artifacts may be loaded."""

from __future__ import annotations
import csv, hashlib, ipaddress, json, os, re, tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from .features import FeatureExtractor, FEATURE_NAMES, FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT
from .urltools import normalize_url, domain_group

THRESHOLDS = {"caution": 40, "danger": 80}
VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z")


class TrainingDataError(ValueError):
    pass


@dataclass(frozen=True)
class Dataset:
    urls: tuple[str, ...]
    labels: tuple[int, ...]
    groups: tuple[str, ...]
    canonical_keys: tuple[str, ...]
    raw_count: int
    duplicate_count: int
    data_sha256: str


@dataclass(frozen=True)
class DatasetSplit:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


def canonical_dataset_url(url):
    p = urlsplit(normalize_url(url))
    host = p.hostname
    try:
        host = ipaddress.ip_address(host).compressed
    except ValueError:
        pass
    if ":" in host:
        host = "[" + host + "]"
    if p.port and (p.scheme, p.port) not in [("https", 443), ("http", 80)]:
        host += ":" + str(p.port)
    return urlunsplit((p.scheme, host, p.path or "/", p.query, ""))


def load_dataset(csv_path):
    try:
        with Path(csv_path).open("rb") as f:
            payload = f.read(200 * 1024 * 1024 + 1)
        if len(payload) > 200 * 1024 * 1024:
            raise TrainingDataError("CSV는 200 MiB 이하여야 합니다.")
        text = payload.decode("utf-8-sig")
    except (OSError, UnicodeError) as e:
        raise TrainingDataError("UTF-8 CSV 파일을 읽을 수 없습니다.") from e
    import io

    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if (
        not reader.fieldnames
        or len(set(reader.fieldnames)) != len(reader.fieldnames)
        or not {"url", "label"} <= set(reader.fieldnames)
    ):
        raise TrainingDataError("CSV에 url,label 열이 필요합니다.")
    urls = []
    labels = []
    groups = []
    keys = []
    seen = {}
    raw = duplicate = 0
    try:
        for row in reader:
            raw += 1
            number = reader.line_num
            if (
                None in row
                or row.get("url") is None
                or row.get("label") is None
                or row["label"].strip() not in ("0", "1")
            ):
                raise TrainingDataError(f"CSV {number}행의 열과 라벨을 확인하세요.")
            label = int(row["label"].strip())
            try:
                normalized = normalize_url(row["url"].strip())
                key = canonical_dataset_url(normalized)
                group = domain_group(normalized)
            except Exception:
                raise TrainingDataError(f"CSV {number}행의 URL 형식을 확인하세요.") from None
            if key in seen:
                if seen[key] != label:
                    raise TrainingDataError(f"CSV {number}행의 중복 URL 라벨이 충돌합니다.")
                duplicate += 1
                continue
            seen[key] = label
            urls.append(normalized)
            labels.append(label)
            groups.append(group)
            keys.append(key)
    except csv.Error:
        raise TrainingDataError("CSV 형식이 올바르지 않습니다.") from None
    if not urls:
        raise TrainingDataError("CSV가 비어 있습니다.")
    return Dataset(
        tuple(urls),
        tuple(labels),
        tuple(groups),
        tuple(keys),
        raw,
        duplicate,
        hashlib.sha256(payload).hexdigest(),
    )


def _valid(y, n=2):
    return all(np.sum(y == label) >= n for label in (0, 1))


def split_dataset(dataset, test_size=0.2, seed=42):
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
        raise TrainingDataError("seed 범위 오류")
    if (
        not isinstance(test_size, (float, int))
        or not np.isfinite(test_size)
        or not 0.1 <= test_size <= 0.5
    ):
        raise TrainingDataError("test-size 범위는 0.1~0.5입니다.")
    y = np.array(dataset.labels)
    g = np.array(dataset.groups)
    if len(y) < 20 or not _valid(y, 5) or any(len(set(g[y == v])) < 4 for v in (0, 1)):
        raise TrainingDataError("최소 20개 URL, 라벨별 5개 URL과 4개 독립 도메인이 필요합니다.")
    for train, test in GroupShuffleSplit(
        n_splits=128, test_size=test_size, random_state=seed
    ).split(y, y, g):
        if (
            _valid(y[train])
            and _valid(y[test])
            and all(len(set(g[train][y[train] == v])) >= 2 for v in (0, 1))
        ):
            assert not set(g[train]) & set(g[test])
            return DatasetSplit(tuple(map(int, train)), tuple(map(int, test)))
    raise TrainingDataError("두 라벨을 포함하는 독립 도메인 분할이 불가능합니다.")


def _metrics(y, p):
    tn, fp, fn, tp = map(int, confusion_matrix(y, p, labels=[0, 1]).ravel())
    return dict(
        accuracy=float(accuracy_score(y, p)),
        precision=float(precision_score(y, p, zero_division=0)),
        recall=float(recall_score(y, p, zero_division=0)),
        f1=float(f1_score(y, p, zero_division=0)),
        false_positive_rate=fp / (fp + tn),
        confusion_matrix=dict(tn=tn, fp=fp, fn=fn, tp=tp),
    )


def _atomic(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name)
    os.close(fd)
    try:
        writer(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def train_model(
    csv_path,
    output_path="artifacts/linkguard.joblib",
    report_path="artifacts/metrics.json",
    *,
    cv_folds=0,
    seed=42,
    test_size=0.2,
    trees=200,
    model_version=None,
):
    if len({Path(p).resolve() for p in [csv_path, output_path, report_path]}) != 3:
        raise TrainingDataError("입력과 출력 경로는 달라야 합니다.")
    if type(trees) != int or not 10 <= trees <= 2000:
        raise TrainingDataError("trees는 10~2000 정수여야 합니다.")
    if type(cv_folds) != int or cv_folds not in [0, *range(2, 11)]:
        raise TrainingDataError("CV는 0 또는 2~10이어야 합니다.")
    if model_version is not None and (
        not isinstance(model_version, str) or not VERSION_PATTERN.fullmatch(model_version)
    ):
        raise TrainingDataError(
            "모델 버전은 영숫자로 시작하는 최대 120자 영숫자/._- 문자열이어야 합니다."
        )
    d = load_dataset(csv_path)
    s = split_dataset(d, test_size, seed)
    e = FeatureExtractor()
    x = np.array([e.vector(u) for u in d.urls], dtype=float)
    y = np.array(d.labels)
    g = np.array(d.groups)
    train = np.array(s.train_indices)
    test = np.array(s.test_indices)
    if x.shape != (len(y), len(FEATURE_NAMES)) or not np.isfinite(x).all():
        raise TrainingDataError("특징 벡터 오류")
    model = RandomForestClassifier(
        n_estimators=trees, random_state=seed, class_weight="balanced", n_jobs=2
    )
    cv = None
    if cv_folds:
        if any(len(set(g[train][y[train] == v])) < cv_folds for v in (0, 1)):
            raise TrainingDataError("CV에 필요한 독립 도메인이 부족합니다.")
        folds = list(
            StratifiedGroupKFold(cv_folds, shuffle=True, random_state=seed).split(
                x[train], y[train], g[train]
            )
        )
        if any(not _valid(y[train][a]) or not _valid(y[train][b]) for a, b in folds):
            raise TrainingDataError("CV 각 구간에 두 라벨이 충분히 필요합니다.")
        results = []
        for a, b in folds:
            assert not set(g[train][a]) & set(g[train][b])
            candidate = clone(model).fit(x[train][a], y[train][a])
            results.append(_metrics(y[train][b], candidate.predict(x[train][b])))
        cv = {"scope": "training_partition_only", "fold_count": cv_folds, "folds": results}
    model.fit(x[train], y[train])
    version = (
        model_version
        or f"rf-rebuilt-{d.data_sha256[:8]}-s{seed}-t{trees}-{RESOURCE_FINGERPRINT[:8]}"
    )
    group_hashes = lambda values: sorted(
        hashlib.sha256(v.encode()).hexdigest() for v in set(values)
    )
    scores = np.rint(model.predict_proba(x[test])[:, 1] * 100).astype(int)
    report = {
        "model_version": version,
        "algorithm": "RandomForestClassifier",
        "sklearn_version": sklearn.__version__,
        "feature_names": list(FEATURE_NAMES),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "resource_fingerprint": RESOURCE_FINGERPRINT,
        "training": {"trees": trees, "seed": seed, "refit_on_holdout": False},
        "dataset": {
            "unique_urls": len(y),
            "input_rows": d.raw_count,
            "duplicate_rows_removed": d.duplicate_count,
            "data_sha256": d.data_sha256,
        },
        "split": {
            "method": "registrable_domain_group_holdout",
            "seed": seed,
            "train_samples": len(train),
            "test_samples": len(test),
            "overlapping_groups": 0,
            "holdout_used_for_fit": False,
            "train_group_hashes": group_hashes(g[train]),
            "test_group_hashes": group_hashes(g[test]),
        },
        "holdout": _metrics(y[test], model.predict(x[test])),
        "cross_validation": cv,
        "warning_policy_holdout": {
            str(t): _metrics(y[test], (scores >= t).astype(int)) for t in (40, 80)
        },
        "limitations": [
            "합성 데이터 지표는 실제 성능이 아닙니다.",
            "40/80 경계와 RF 점수는 보정되지 않은 시제품 신호입니다.",
            "도메인 분리만으로 모든 캠페인/시간 누수를 제거할 수 없습니다.",
        ],
    }
    artifact = {
        "artifact_version": 1,
        "feature_names": list(FEATURE_NAMES),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "resource_fingerprint": RESOURCE_FINGERPRINT,
        "model_version": version,
        "model": model,
        "thresholds": THRESHOLDS,
        "metadata": {
            "sklearn_version": sklearn.__version__,
            "data_sha256": d.data_sha256,
            "holdout_used_for_fit": False,
            "training_sample_count": len(train),
            "seed": seed,
            "trees": trees,
        },
    }
    _atomic(output_path, lambda p: joblib.dump(artifact, p, compress=3))
    _atomic(
        report_path,
        lambda p: Path(p).write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
        ),
    )
    return report
