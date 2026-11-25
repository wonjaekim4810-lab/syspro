import unittest, tempfile, socket
from pathlib import Path
from unittest.mock import patch
import joblib, numpy as np, sklearn
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
from linkguard.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    RESOURCE_FINGERPRINT,
    FeatureExtractor,
)
from linkguard.model import URLDetector, ModelUnavailableError
from server import create_app


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "model.joblib"
        x = np.array(
            [
                FeatureExtractor().vector(u)
                for u in [
                    "https://docs.example/help",
                    "https://guide.example",
                    "http://parcel-verify.example/login",
                    "http://192.0.2.1/verify",
                ]
            ]
        )
        m = RandomForestClassifier(n_estimators=10, random_state=1).fit(x, [0, 0, 1, 1])
        self.artifact = {
            "artifact_version": 1,
            "feature_names": list(FEATURE_NAMES),
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "resource_fingerprint": RESOURCE_FINGERPRINT,
            "model_version": "synthetic-test-only",
            "model": m,
            "thresholds": {"caution": 40, "danger": 80},
            "metadata": {"sklearn_version": sklearn.__version__},
        }
        joblib.dump(self.artifact, self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_prediction_contract(self):
        with TestClient(create_app(self.path)) as c:
            self.assertEqual(c.get("/health").json()["status"], "ready")
            r = c.post("/predict", json={"url": "HTTPS://Example.com/a?x=1#f"})
            self.assertEqual(r.status_code, 200)
            j = r.json()
            self.assertEqual(j["url"], "https://example.com/a?x=1#f")
            self.assertIs(type(j["score"]), int)
            self.assertTrue(0 <= j["score"] <= 100)
            self.assertTrue(1 <= len(j["reasons"]) <= 12)
            self.assertEqual(set(j), {"url", "status", "score", "reasons", "model_version"})

    def test_missing_model_503_no_fake_score(self):
        with TestClient(create_app(self.path.parent / "missing")) as c:
            self.assertEqual(c.get("/health").json()["status"], "model_unavailable")
            r = c.post("/predict", json={"url": "https://example.com"})
            self.assertEqual(r.status_code, 503)
            self.assertNotIn("score", r.json())

    def test_invalid_inputs_generic_422(self):
        with TestClient(create_app(self.path)) as c:
            for body in [
                {"url": "javascript:alert(1)"},
                {"url": 4},
                {"url": True},
                {"url": "https://example.com", "extra": 1},
                {},
            ]:
                r = c.post("/predict", json=body)
                self.assertEqual(r.status_code, 422)
                self.assertNotIn("javascript", r.text)

    def test_oversize_and_no_cors(self):
        with TestClient(create_app(self.path)) as c:
            self.assertEqual(c.post("/predict", content=b"a" * 16385).status_code, 413)
            self.assertNotIn(
                "access-control-allow-origin",
                c.get("/health", headers={"Origin": "https://other.example"}).headers,
            )

    def test_incompatible_artifacts_fail_closed(self):
        for key, value in [
            ("feature_names", []),
            ("resource_fingerprint", "wrong"),
            ("model_version", "bad\nversion"),
            ("thresholds", {}),
        ]:
            bad = dict(self.artifact)
            bad[key] = value
            joblib.dump(bad, self.path)
            with self.assertRaises(ModelUnavailableError):
                URLDetector.load(self.path)

    def test_corrupt_artifact(self):
        self.path.write_bytes(b"not a model")
        with self.assertRaises(ModelUnavailableError):
            URLDetector.load(self.path)

    def test_prediction_never_resolves_url(self):
        d = URLDetector.load(self.path)
        with patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")
        ), patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ):
            self.assertIn("score", d.predict("https://safe.example/a"))

    def test_bad_prediction_disables_model_generic_503(self):
        with TestClient(create_app(self.path)) as c:
            with patch.object(
                c.app.state.detector, "predict", side_effect=RuntimeError("private-url-token")
            ):
                r = c.post("/predict", json={"url": "https://example.com"})
                self.assertEqual(r.status_code, 503)
                self.assertNotIn("private", r.text)

    def test_busy_gate_returns_503(self):
        import asyncio

        with TestClient(create_app(self.path)) as c:
            c.app.state.gate = asyncio.Semaphore(0)
            self.assertEqual(
                c.post("/predict", json={"url": "https://example.com"}).status_code, 503
            )

    def test_chunked_asgi_body_limit_prevents_app_call(self):
        import asyncio
        from server import BodyLimit

        sent = []
        chunks = iter(
            [
                {"type": "http.request", "body": b"a" * 10000, "more_body": True},
                {"type": "http.request", "body": b"b" * 7000, "more_body": False},
            ]
        )

        async def downstream(scope, receive, send):
            raise AssertionError("oversize body reached parser")

        async def receive():
            return next(chunks)

        async def send(message):
            sent.append(message)

        asyncio.run(BodyLimit(downstream)({"type": "http"}, receive, send))
        self.assertEqual(sent[0]["status"], 413)

    def test_content_length_rejected_without_reading_body(self):
        import asyncio
        from server import BodyLimit

        for header, status in [(b"16385", 413), (b"-1", 400), (b"bad", 400)]:
            with self.subTest(header=header):
                sent = []

                async def downstream(scope, receive, send):
                    raise AssertionError("rejected request reached app")

                async def receive():
                    raise AssertionError("rejected header triggered body read")

                async def send(message):
                    sent.append(message)

                asyncio.run(
                    BodyLimit(downstream)(
                        {"type": "http", "headers": [(b"content-length", header)]}, receive, send
                    )
                )
                self.assertEqual(sent[0]["status"], status)
