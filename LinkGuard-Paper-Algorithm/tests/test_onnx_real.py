"""Optional real-runtime contract tests; fixed graphs are not trained DL models."""

from pathlib import Path
import importlib.util
import math
import tempfile
import unittest

from linkguard.adapters import build_adapter
from linkguard.model import ModelUnavailableError
from linkguard.registered_detector import RegisteredDetector
from linkguard.registry import SQLiteRegistry

AVAILABLE = all(importlib.util.find_spec(name) for name in ("onnx", "onnxruntime"))


@unittest.skipUnless(AVAILABLE, "Optional real ONNX tests require onnx and onnxruntime")
class RealOnnxContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = SQLiteRegistry(self.root / "models.sqlite3")

    def graph(self, kind):
        import numpy as np
        import onnx
        from onnx import helper, numpy_helper, TensorProto

        outputs = 2 if kind == "softmax" else 1
        bias = np.array([2.0, 0.0] if outputs == 2 else [0.0], dtype=np.float32)
        weights = np.zeros((40, outputs), dtype=np.float32)
        initializers = [numpy_helper.from_array(weights, "W"), numpy_helper.from_array(bias, "B")]
        nodes = [helper.make_node("Gemm", ["features", "W", "B"], ["logits"])]
        if kind == "softmax":
            nodes.append(helper.make_node("Softmax", ["logits"], ["probability"], axis=1))
        elif kind == "boolean":
            initializers.append(numpy_helper.from_array(np.array([0.0], dtype=np.float32), "zero"))
            nodes.append(helper.make_node("Greater", ["logits", "zero"], ["probability"]))
        else:
            nodes.append(helper.make_node("Sigmoid", ["logits"], ["probability"]))
        graph = helper.make_graph(
            nodes,
            "fixed_contract_fixture",
            [helper.make_tensor_value_info("features", TensorProto.FLOAT, [None, 40])],
            [
                helper.make_tensor_value_info(
                    "probability",
                    TensorProto.BOOL if kind == "boolean" else TensorProto.FLOAT,
                    [None, outputs],
                )
            ],
            initializer=initializers,
        )
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        model.ir_version = 8
        onnx.checker.check_model(model)
        path = self.root / (kind + ".onnx")
        onnx.save(model, path)
        return path

    def test_real_softmax_graph_db_activation_and_positive_class(self):
        path = self.graph("softmax")
        first = self.registry.register(
            name="fixture", version="onnx-v1", backend="onnx", artifact_path=path
        )
        self.registry.activate(first.id, build_adapter)
        detector = RegisteredDetector(self.registry)
        result = detector.predict("https://www.example.com")
        self.assertEqual(result["score"], round(100 / (1 + math.exp(2))))
        self.assertEqual(result["status"], "safe")
        second = self.registry.register(
            name="fixture",
            version="onnx-v2",
            backend="onnx",
            artifact_path=path,
            positive_class_index=0,
        )
        self.registry.activate(second.id, build_adapter)
        changed = detector.predict("https://www.example.com")
        self.assertEqual(changed["score"], round(100 / (1 + math.exp(-2))))
        self.assertEqual(changed["model_version"], "onnx-v2")

    def test_real_sigmoid_scalar_contract(self):
        record = self.registry.register(
            name="scalar", version="dl-v1", backend="onnx", artifact_path=self.graph("sigmoid")
        )
        adapter = build_adapter(record)
        self.assertAlmostEqual(adapter.probability("", [0.0] * 40), 0.5)

    def test_real_boolean_label_output_rejected(self):
        record = self.registry.register(
            name="labels", version="bad-v1", backend="onnx", artifact_path=self.graph("boolean")
        )
        with self.assertRaises(ModelUnavailableError):
            self.registry.activate(record.id, build_adapter)
        self.assertIsNone(self.registry.get_active())
