"""Regression checks for corrupted model metadata and live registry refresh."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from pack_joblib import export_pretrained
from linkguard.registry import SQLiteRegistry
from linkguard.adapters import build_adapter
from linkguard.model import ModelUnavailableError
from linkguard.registered_detector import RegisteredDetector


class SlotValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        rng = np.random.default_rng(5)
        self.model = LogisticRegression().fit(rng.normal(size=(20, 40)), [0, 1] * 10)
        self.file = export_pretrained(self.model, self.root / "ok.joblib", "ml-v1")
        self.db = SQLiteRegistry(self.root / "models.sqlite3")
        self.record = self.db.register(
            name="ml", version="ml-v1", backend="joblib", artifact_path=self.file
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_corrupt_metadata_fails_before_inference(self):
        for bad in [
            replace(self.record, version="\nsecret"),
            replace(self.record, version="한글"),
            replace(self.record, positive_class_index=True),
            replace(self.record, sha256="wrong"),
        ]:
            with self.subTest(bad=bad), self.assertRaises(ModelUnavailableError):
                build_adapter(bad)

    def test_artifact_version_type_and_value_are_strict(self):
        original = joblib.load(self.file)
        for value in [None, True, 2, "1"]:
            bundle = dict(original)
            bundle["artifact_version"] = value
            path = self.root / f"bad-{str(value)}.joblib"
            joblib.dump(bundle, path)
            record = self.db.register(
                name="ml", version=f"bad-{str(value)}", backend="joblib", artifact_path=path
            )
            with self.assertRaises(ModelUnavailableError):
                build_adapter(record)

    def test_wrong_named_feature_order_is_rejected(self):
        self.model.feature_names_in_ = np.array([f"wrong{i}" for i in range(40)])
        with self.assertRaises(ValueError):
            export_pretrained(self.model, self.root / "wrong.joblib", "wrong-v1")

    def test_metadata_change_is_seen_and_bad_selection_never_uses_cached_model(self):
        active = self.db.activate(self.record.id, build_adapter)

        class ExternalDB:
            value = active

            def get_active(self):
                return self.value

        registry = ExternalDB()
        detector = RegisteredDetector(registry)
        self.assertTrue(detector.ready())
        registry.value = replace(active, sha256="0" * 64)
        self.assertFalse(detector.ready())
        with self.assertRaises(ModelUnavailableError):
            detector.predict("https://example.com")
        registry.value = active
        self.assertTrue(detector.ready())


if __name__ == "__main__":
    unittest.main()
