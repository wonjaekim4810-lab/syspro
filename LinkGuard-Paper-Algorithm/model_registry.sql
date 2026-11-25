-- SQLite example only. Model weights live in immutable local artifact files.
CREATE TABLE IF NOT EXISTS model_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    backend TEXT NOT NULL CHECK (backend IN ('joblib', 'onnx', 'custom')),
    input_kind TEXT NOT NULL CHECK (input_kind IN ('features40', 'url_text')),
    artifact_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    feature_schema_version TEXT NOT NULL,
    resource_fingerprint TEXT NOT NULL,
    positive_class_index INTEGER NOT NULL CHECK (positive_class_index IN (0, 1)),
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
    UNIQUE (name, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_model
    ON model_registry(active) WHERE active = 1;
