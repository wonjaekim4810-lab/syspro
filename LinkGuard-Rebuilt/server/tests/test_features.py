"""Behavior checks for rebuilt lexical features; not an accuracy benchmark."""

import math
import socket
import unittest
from unittest.mock import patch

from linkguard.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    RESOURCE_FINGERPRINT,
    FeatureExtractor,
)
from linkguard.nlp import (
    BRANDS,
    KEYWORDS,
    bigram_score,
    bounded_edit_distance,
    decompose,
    is_random_word,
    raw_tokens,
    similar_matches,
)


class NLPTests(unittest.TestCase):
    def test_wdm_preserves_known_words_and_uncovered_spans(self):
        self.assertEqual(decompose("secure1login"), ("secure", "login"))
        self.assertEqual(decompose("paypalverify"), ("paypal", "verify"))
        self.assertEqual(decompose("xsecurelogin"), ("x", "secure", "login"))
        self.assertEqual(decompose("authentication"), ("authentication",))
        self.assertEqual(decompose("secure"), ("secure",))
        self.assertEqual(decompose("123"), ())
        self.assertEqual(decompose("q" * 81), ("q" * 81,))

    def test_random_word_model_is_smoothed_bounded_and_experimental(self):
        self.assertGreater(bigram_score("delivery"), bigram_score("xqzvjkbn"))
        self.assertTrue(is_random_word("xqzvjkbn"))
        self.assertFalse(is_random_word("delivery"))
        self.assertFalse(is_random_word("securelogin"))
        self.assertFalse(is_random_word("qzx"))
        self.assertEqual(bigram_score("123"), 0)
        self.assertTrue(math.isfinite(bigram_score("z" * 4096)))

    def test_mam_edit_distance_excludes_exact_matches(self):
        self.assertEqual(bounded_edit_distance("goggle", "google"), 1)
        self.assertEqual(bounded_edit_distance("login", "login", 0), 0)
        self.assertEqual(bounded_edit_distance("kitten", "sitting", 2), 3)
        self.assertIn("google", similar_matches("goggle", BRANDS))
        self.assertIn("login", similar_matches("logim", KEYWORDS))
        self.assertEqual(similar_matches("google", BRANDS), ())
        self.assertEqual(similar_matches("x" * 65, BRANDS), ())

    def test_tokenizer_decodes_once(self):
        self.assertEqual(raw_tokens("secure%6Cogin/a12?x=9"), ("securelogin", "a12", "x", "9"))
        self.assertEqual(raw_tokens("%2520"), ("20",))


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()

    def test_schema_exactly_forty_and_stable_finite_order(self):
        self.assertEqual(len(FEATURE_NAMES), 40)
        self.assertEqual(len(set(FEATURE_NAMES)), 40)
        self.assertEqual(FEATURE_NAMES[-2:], ("uses_https", "host_is_ip"))
        self.assertEqual(FEATURE_SCHEMA_VERSION, "sahingoz-adapted-v1-rebuilt")
        self.assertRegex(RESOURCE_FINGERPRINT, "^[0-9a-f]{64}$")
        result = self.extractor.extract("https://example.com")
        self.assertEqual(tuple(result), FEATURE_NAMES)
        self.assertEqual(self.extractor.vector("https://example.com"), list(result.values()))
        self.assertTrue(all(type(x) is float and math.isfinite(x) for x in result.values()))

    def test_simple_raw_word_statistics_are_inspectable(self):
        x = self.extractor.extract("https://example.com")
        for key, expected in [
            ("raw_word_count", 2),
            ("average_word_length", 5),
            ("longest_word_length", 7),
            ("shortest_word_length", 3),
            ("word_length_std", 2),
            ("length_domain", 7),
            ("known_tld", 1),
            ("count_slash", 2),
            ("uses_https", 1),
            ("host_is_ip", 0),
        ]:
            self.assertEqual(x[key], expected)

    def test_compound_keyword_and_typo_features(self):
        x = self.extractor.extract("http://secure1login.example/verify")
        self.assertEqual(x["adjacent_word_count"], 1)
        self.assertEqual(x["average_adjacent_word_length"], 11)
        self.assertEqual(x["separated_word_count"], 2)
        self.assertEqual(x["keyword_count"], 3)
        self.assertEqual(x["target_keyword_count"], 2)
        self.assertEqual(
            self.extractor.extract("https://goggle.com")["similar_brand_name_count"], 1
        )

    def test_random_words_removed_before_mam(self):
        self.assertTrue(is_random_word("kqkao"))
        self.assertIn("kakao", similar_matches("kqkao", BRANDS))
        x = self.extractor.extract("https://kqkao.example")
        self.assertEqual(x["random_word_count"], 1)
        self.assertEqual(x["similar_brand_name_count"], 0)
        self.assertEqual(x["random_domain"], 1)

    def test_brand_membership_not_ownership_and_target_scope(self):
        official = self.extractor.extract("https://www.google.com")
        self.assertEqual(official["brand_check_domain"], 1)
        self.assertEqual(official["target_brand_name_count"], 1)
        fake = self.extractor.extract("https://google.example")
        self.assertEqual(fake["brand_check_domain"], 0)
        self.assertEqual(fake["target_brand_name_count"], 1)
        sub = self.extractor.extract("https://google.other.example")
        self.assertEqual(sub["brand_name_count"], 1)
        self.assertEqual(sub["target_brand_name_count"], 0)
        self.assertEqual(self.extractor.extract("https://naver.com")["brand_check_domain"], 1)

    def test_component_digits_lengths_and_full_url_symbols(self):
        tail = "/p34?q=5&v_6=7"
        x = self.extractor.extract("https://s1.s2.a12.example.com" + tail + "#f8")
        self.assertEqual(x["digit_count_domain"], 0)
        self.assertEqual(x["digit_count_subdomain"], 4)
        self.assertEqual(x["digit_count_path"], 5)
        self.assertEqual(x["subdomain_count"], 3)
        self.assertEqual(x["length_path"], len(tail))
        self.assertEqual(x["count_question"], 1)
        self.assertEqual(x["count_equal"], 2)
        special = self.extractor.extract("https://www.com.example.com/a-aa/@x")
        self.assertEqual(special["www_in_domain_subdomain"], 1)
        self.assertEqual(special["com_in_domain_subdomain"], 1)
        self.assertEqual(special["count_hyphen"], 1)
        self.assertEqual(special["count_at"], 1)
        self.assertEqual(special["consecutive_character_repeat"], 4)

    def test_idn_ip_ipv6_private_suffix_inputs(self):
        for url, puny, ip in [
            ("https://bücher.de", 1, 0),
            ("http://192.0.2.10/verify", 0, 1),
            ("https://[2001:db8::1]/", 0, 1),
            ("https://team.github.io/", 0, 0),
        ]:
            with self.subTest(url=url):
                x = self.extractor.extract(url)
                self.assertEqual(x["punycode"], puny)
                self.assertEqual(x["host_is_ip"], ip)
                self.assertTrue(all(math.isfinite(v) for v in x.values()))
        self.assertEqual(self.extractor.extract("https://team.github.io")["length_domain"], 4)
        self.assertEqual(self.extractor.extract("https://www.example.co.uk")["length_domain"], 7)

    def test_explanations_are_factual_limited_observations(self):
        reasons = self.extractor.explain(
            "http://a1.b2.xn--naver-verify.example/goggle/login?" + "q" * 100
        )
        self.assertTrue(1 <= len(reasons) <= 12)
        self.assertTrue(all(0 < len(x.encode("utf-16-le")) // 2 <= 500 for x in reasons))
        self.assertTrue(any("HTTP" in x for x in reasons))
        self.assertFalse(any("97.98" in x or "안전합니다" in x for x in reasons))

    def test_feature_extraction_makes_no_dns_or_network_connections(self):
        with patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("No DNS")
        ), patch.object(socket, "create_connection", side_effect=AssertionError("No connection")):
            self.assertEqual(
                len(self.extractor.vector("https://a.brand.project.github.io/p?q=1")), 40
            )

    def test_maximum_length_token_remains_finite(self):
        prefix = "https://example.com/"
        vector = self.extractor.vector(prefix + "q" * (4096 - len(prefix)))
        self.assertEqual(len(vector), 40)
        self.assertTrue(all(math.isfinite(x) for x in vector))


if __name__ == "__main__":
    unittest.main()
