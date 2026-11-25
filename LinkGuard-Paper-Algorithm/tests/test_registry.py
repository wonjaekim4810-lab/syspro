"""Synthetic model-slot plumbing only: these are not phishing performance tests."""

from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from fastapi.testclient import TestClient
from pack_joblib import export_pretrained
from linkguard.adapters import build_adapter, JoblibAdapter, OnnxFeatureAdapter
from linkguard.features import FeatureExtractor
from linkguard.model import ModelUnavailableError
from linkguard.registry import SQLiteRegistry
from linkguard.registered_detector import RegisteredDetector
from server import create_app
from explain_url import explain_url


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = SQLiteRegistry(self.root / "models.sqlite3")
        # Deliberately generic sklearn estimator: not a RandomForest-only serving slot.
        rng = np.random.default_rng(1)
        x = rng.normal(size=(30, 40))
        y = np.array([0, 1] * 15)
        self.model = LogisticRegression(random_state=42).fit(x, y)
        self.path = export_pretrained(self.model, self.root / "ml-v1.joblib", "ml-v1")

    def tearDown(self):
        self.temp.cleanup()

    def register(self, path=None, version="ml-v1", **kwargs):
        return self.registry.register(
            name="test",
            version=version,
            backend="joblib",
            artifact_path=path or self.path,
            **kwargs
        )

    def test_absent_registry_reports_unavailable_without_making_fake_prediction(self):
        detector = RegisteredDetector(self.registry)
        self.assertFalse(detector.ready())
        with self.assertRaises(ModelUnavailableError):
            detector.predict("https://example.com")
        self.assertFalse(self.registry.database.exists())

    def test_external_sklearn_export_register_activate_predict_matches_real_estimator(self):
        record = self.register()
        self.assertFalse(record.active)
        record = self.registry.activate(record.id, build_adapter)
        detector = RegisteredDetector(self.registry)
        result = detector.predict("https://example.com")
        vector = FeatureExtractor().vector("https://example.com")
        expected = round(float(self.model.predict_proba([vector])[0, 1]) * 100)
        self.assertEqual(result["score"], expected)
        self.assertEqual(result["model_version"], "ml-v1")
        self.assertEqual(set(result), {"url", "status", "score", "reasons", "model_version"})
        self.assertTrue(detector.ready())

    def test_db_can_switch_active_model_without_restarting_service(self):
        first = self.register()
        self.registry.activate(first.id, build_adapter)
        detector = RegisteredDetector(self.registry)
        self.assertEqual(detector.predict("https://example.com")["model_version"], "ml-v1")
        second_path = export_pretrained(self.model, self.root / "ml-v2.joblib", "ml-v2")
        second = self.register(second_path, "ml-v2")
        self.registry.activate(second.id, build_adapter)
        self.assertEqual(detector.predict("https://example.com")["model_version"], "ml-v2")
        self.assertEqual(sum(r.active for r in self.registry.list_models()), 1)

    def test_failed_activation_keeps_previously_active_model(self):
        first = self.register()
        self.registry.activate(first.id, build_adapter)
        bad = self.root / "bad.joblib"
        bad.write_bytes(b"notamodel")
        second = self.register(bad, "bad-v1")
        with self.assertRaises(ModelUnavailableError):
            self.registry.activate(second.id, build_adapter)
        self.assertEqual(self.registry.get_active().id, first.id)

    def test_duplicate_name_version_never_overwrites_existing_record(self):
        first = self.register()
        with self.assertRaises(Exception):
            self.register()
        self.assertEqual([x.id for x in self.registry.list_models()], [first.id])

    def test_tamper_checksum_wrong_schema_wrong_positiveclass_and_missing_file_rejected(self):
        record = self.register()
        for changed in [
            replace(record, sha256="0" * 64),
            replace(record, feature_schema_version="other"),
            replace(record, resource_fingerprint="f" * 64),
            replace(record, positive_class_index=0),
            replace(record, artifact_path=str(self.root / "missing")),
        ]:
            with self.subTest(changed=changed), self.assertRaises(ModelUnavailableError):
                build_adapter(changed)
        self.path.write_bytes(b"changed after registration")
        with self.assertRaises(ModelUnavailableError):
            build_adapter(record)

    def test_custom_url_text_slot_is_explicitly_unimplemented_and_cannot_activate(self):
        record = self.registry.register(
            name="neural",
            version="dl-v1",
            backend="custom",
            input_kind="url_text",
            artifact_path=self.path,
        )
        with self.assertRaises(ModelUnavailableError):
            self.registry.activate(record.id, build_adapter)
        self.assertIsNone(self.registry.get_active())

    def test_external_export_rejects_wrong_dimensions_or_order(self):
        wrong = LogisticRegression().fit(np.arange(30).reshape(-1, 1), [0, 1] * 15)
        with self.assertRaises(ValueError):
            export_pretrained(wrong, self.root / "wrong.joblib", "wrong-v1")
        with self.assertRaises(ValueError):
            export_pretrained(self.model, self.root / "badversion.joblib", "한글")

    def test_api_db_slot_missing_then_activate_then_ready(self):
        with TestClient(create_app(registry=self.registry)) as client:
            self.assertEqual(client.get("/health").json()["status"], "model_unavailable")
            self.assertEqual(
                client.post("/predict", json={"url": "https://example.com"}).status_code, 503
            )
            record = self.register()
            self.registry.activate(record.id, build_adapter)
            self.assertEqual(client.get("/health").json()["status"], "ready")
            result = client.post("/predict", json={"url": "https://example.com"})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["model_version"], "ml-v1")
            self.assertEqual(
                client.post("/predict", json={"url": "javascript:alert(1)"}).status_code, 422
            )

    def test_registry_protocol_can_be_implemented_without_sqlite(self):
        record = self.register()
        active = replace(record, active=True)

        class MemoryRegistry:
            def get_active(self):
                return active

        self.assertEqual(
            RegisteredDetector(MemoryRegistry()).predict("https://example.com")["model_version"],
            "ml-v1",
        )

    def test_trace_has_forty_features_but_no_risk_score(self):
        trace = explain_url("http://securelogin.example/verify")
        self.assertEqual(len(trace["features"]), 40)
        self.assertNotIn("score", trace)
        segments = [step["wdm"] for step in trace["steps"]]
        self.assertIn(["secure", "login"], segments)

    def test_optional_onnx_output_contract_with_fake_session_not_real_runtime_validation(self):
        # This tests adapter decoding only; real exported ONNX networks are not bundled.
        class FakeSession:
            output = np.array([[0.25, 0.75]])

            def run(self, unused, feeds):
                self.last = next(iter(feeds.values()))
                return [self.output]

        adapter = OnnxFeatureAdapter()
        adapter.session = FakeSession()
        adapter.input_name = "features"
        adapter.positive_index = 1
        self.assertEqual(adapter.probability("", [0.0] * 40), 0.75)
        self.assertEqual(adapter.session.last.dtype, np.float32)
        for value in [
            np.array([[0.1, 0.2]]),
            np.array([[2.0]]),
            np.zeros((2, 2)),
            np.array([[float("nan")]]),
        ]:
            adapter.session.output = value
            with self.assertRaises(ModelUnavailableError):
                adapter.probability("", [0.0] * 40)
        adapter.session.output = np.array([[0.3]])
        self.assertEqual(adapter.probability("", [0.0] * 40), 0.3)


if __name__ == "__main__":
    unittest.main()
