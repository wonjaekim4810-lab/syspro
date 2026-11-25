"""Model metadata registry; weights remain trusted local files, not SQL values."""

from __future__ import annotations
from dataclasses import dataclass, replace
from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
import sqlite3
from typing import Callable, Protocol
from .features import FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT


@dataclass(frozen=True)
class ModelRecord:
    id: int
    name: str
    version: str
    backend: str
    input_kind: str
    artifact_path: str
    sha256: str
    feature_schema_version: str
    resource_fingerprint: str
    positive_class_index: int
    active: bool


class ModelRegistry(Protocol):
    """Implement this interface for PostgreSQL/MySQL/existing organizational DBs."""

    def get_active(self) -> ModelRecord | None: ...


class SQLiteRegistry:
    def __init__(self, database: str | Path):
        self.database = Path(database)

    def initialize(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS model_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, version TEXT NOT NULL,
                backend TEXT NOT NULL CHECK(backend IN ('joblib','onnx','custom')),
                input_kind TEXT NOT NULL CHECK(input_kind IN ('features40','url_text')),
                artifact_path TEXT NOT NULL, sha256 TEXT NOT NULL,
                feature_schema_version TEXT NOT NULL, resource_fingerprint TEXT NOT NULL,
                positive_class_index INTEGER NOT NULL CHECK(positive_class_index IN (0,1)),
                active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1)),
                UNIQUE(name,version))"""
            )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS one_active_model ON model_registry(active) WHERE active=1"
            )

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _record(row) -> ModelRecord | None:
        if row is None:
            return None
        data = dict(row)
        data["active"] = bool(data["active"])
        return ModelRecord(**data)

    def register(
        self,
        *,
        name: str,
        version: str,
        backend: str,
        artifact_path: str | Path,
        input_kind: str = "features40",
        feature_schema_version: str = FEATURE_SCHEMA_VERSION,
        resource_fingerprint: str = RESOURCE_FINGERPRINT,
        positive_class_index: int = 1,
    ) -> ModelRecord:
        token = r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}"
        if not re.fullmatch(token, name) or not re.fullmatch(token, version):
            raise ValueError(
                "모델 이름과 버전은 영숫자로 시작하는 최대 120자 영숫자/._- 문자열이어야 합니다."
            )
        if backend not in {"joblib", "onnx", "custom"} or input_kind not in {
            "features40",
            "url_text",
        }:
            raise ValueError("지원하지 않는 backend/input_kind입니다.")
        if backend != "custom" and input_kind != "features40":
            raise ValueError("기본 ML/ONNX 어댑터는 features40 입력을 사용합니다.")
        if type(positive_class_index) is not int or positive_class_index not in (0, 1):
            raise ValueError("양성 클래스 인덱스는 0 또는 1이어야 합니다.")
        if (
            not feature_schema_version
            or len(feature_schema_version) > 120
            or not re.fullmatch("[a-f0-9]{64}", resource_fingerprint)
        ):
            raise ValueError("입력 스키마 및 리소스 지문을 확인하세요.")
        path = Path(artifact_path).resolve()
        if not path.is_file() or not 0 < path.stat().st_size <= 256 * 1024 * 1024:
            raise ValueError("모델 파일은 0바이트 초과, 256 MiB 이하의 로컬 파일이어야 합니다.")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.initialize()
        with self._connection() as db:
            cursor = db.execute(
                """INSERT INTO model_registry
                (name,version,backend,input_kind,artifact_path,sha256,feature_schema_version,resource_fingerprint,positive_class_index)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    name,
                    version,
                    backend,
                    input_kind,
                    str(path),
                    digest,
                    feature_schema_version,
                    resource_fingerprint,
                    positive_class_index,
                ),
            )
            row = db.execute(
                "SELECT * FROM model_registry WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
        return self._record(row)

    def list_models(self) -> list[ModelRecord]:
        if not self.database.exists():
            return []
        with self._connection() as db:
            return [
                self._record(row) for row in db.execute("SELECT * FROM model_registry ORDER BY id")
            ]

    def get_active(self) -> ModelRecord | None:
        if not self.database.exists():
            return None
        with self._connection() as db:
            return self._record(
                db.execute("SELECT * FROM model_registry WHERE active=1").fetchone()
            )

    def activate(self, model_id: int, validator: Callable[[ModelRecord], object]) -> ModelRecord:
        with self._connection() as db:
            before = self._record(
                db.execute("SELECT * FROM model_registry WHERE id=?", (model_id,)).fetchone()
            )
        if before is None:
            raise ValueError("모델 ID를 찾을 수 없습니다.")
        validator(before)  # A failed load never deactivates the previously working model.
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._record(
                db.execute("SELECT * FROM model_registry WHERE id=?", (model_id,)).fetchone()
            )
            if current != before:
                raise ValueError("검증 중 모델 메타데이터가 변경되었습니다. 다시 시도하세요.")
            db.execute("UPDATE model_registry SET active=0 WHERE active=1")
            db.execute("UPDATE model_registry SET active=1 WHERE id=?", (model_id,))
        return replace(before, active=True)
