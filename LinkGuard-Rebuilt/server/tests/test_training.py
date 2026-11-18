import unittest, tempfile, csv, json
from pathlib import Path
import joblib
from linkguard.training import (
    load_dataset,
    split_dataset,
    train_model,
    TrainingDataError,
    canonical_dataset_url,
)
from linkguard.model import URLDetector


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def csv(self, rows):
        p = self.root / "urls.csv"
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "label"])
            w.writerows(rows)
        return p

    def rows(self):
        return [
            (
                f'{"https" if y==0 else "http"}://{"docs" if y==0 else "parcel-verify"}{i}.example/{path}',
                y,
            )
            for y in (0, 1)
            for i in range(12)
            for path in ["help", "login"]
        ]

    def test_group_split_disjoint_and_repeatable(self):
        d = load_dataset(self.csv(self.rows()))
        s = split_dataset(d)
        self.assertEqual(s, split_dataset(d))
        self.assertFalse(
            {d.groups[i] for i in s.train_indices} & {d.groups[i] for i in s.test_indices}
        )

    def test_duplicate_key_keeps_normalized_representative(self):
        d = load_dataset(
            self.csv([("https://EXAMPLE.com:443#one", 0), ("https://example.com/#two", 0)])
        )
        self.assertEqual(d.duplicate_count, 1)
        self.assertEqual(d.urls[0], "https://example.com:443#one")

    def test_conflicting_labels_no_raw_url(self):
        with self.assertRaises(TrainingDataError) as c:
            load_dataset(
                self.csv([("https://private.example", 0), ("https://private.example:443/", 1)])
            )
        self.assertNotIn("private", str(c.exception))

    def test_ipv6_alias_key(self):
        self.assertEqual(
            canonical_dataset_url("https://[2001:0db8::1]:443#x"),
            canonical_dataset_url("https://[2001:db8::1]/"),
        )

    def test_tiny_dataset_rejected(self):
        with self.assertRaises(TrainingDataError):
            split_dataset(
                load_dataset(self.csv([("https://a.example", 0), ("https://b.example", 1)]))
            )

    def test_invalid_input_rejected(self):
        for row in [("javascript:alert(1)", 0), ("https://example.com", 2)]:
            with self.assertRaises(TrainingDataError):
                load_dataset(self.csv([row]))

    def test_train_cv_artifact_and_report(self):
        out = self.root / "m.joblib"
        rep = self.root / "r.json"
        r = train_model(self.csv(self.rows()), out, rep, trees=10, cv_folds=2)
        self.assertFalse(r["split"]["holdout_used_for_fit"])
        self.assertEqual(r["split"]["overlapping_groups"], 0)
        self.assertEqual(r["cross_validation"]["scope"], "training_partition_only")
        self.assertEqual(set(r["warning_policy_holdout"]), {"40", "80"})
        a = joblib.load(out)
        self.assertEqual(a["metadata"]["training_sample_count"], r["split"]["train_samples"])
        self.assertEqual(
            URLDetector.load(out).predict("https://example.com")["model_version"],
            r["model_version"],
        )
        self.assertEqual(json.loads(rep.read_text())["model_version"], r["model_version"])

    def test_bad_options_and_same_paths(self):
        p = self.csv(self.rows())
        for kwargs in [
            {"trees": 1},
            {"model_version": "bad\nversion"},
            {"model_version": "한글"},
            {"cv_folds": 1},
        ]:
            with self.assertRaises(TrainingDataError):
                train_model(p, self.root / "m", self.root / "r", **kwargs)
        with self.assertRaises(TrainingDataError):
            train_model(p, p, self.root / "r")
