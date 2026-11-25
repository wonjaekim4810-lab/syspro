"""Rebuilt 40-feature URL extractor adapted from Sahingoz et al. Table 2.

The first 38 categories use explicit local semantics. Alexa's two unavailable
positions are replaced by HTTPS/IP flags. This is not a paper reproduction.
"""

from __future__ import annotations

import hashlib
from importlib import resources
import math
import statistics
from urllib.parse import urlsplit
import tldextract

from .nlp import (
    BRANDS,
    DICTIONARY,
    KEYWORDS,
    KNOWN_TLDS,
    OFFICIAL_DOMAINS,
    RESOURCE_DIR,
    decompose,
    is_random_word,
    letters_only,
    raw_tokens,
    similar_matches,
)
from .urltools import parse_url

FEATURE_SCHEMA_VERSION = "sahingoz-adapted-v1-rebuilt"
FEATURE_NAMES = (
    "raw_word_count",
    "brand_check_domain",
    "average_word_length",
    "longest_word_length",
    "shortest_word_length",
    "word_length_std",
    "adjacent_word_count",
    "average_adjacent_word_length",
    "separated_word_count",
    "keyword_count",
    "brand_name_count",
    "similar_keyword_count",
    "similar_brand_name_count",
    "random_word_count",
    "target_brand_name_count",
    "target_keyword_count",
    "other_word_count",
    "digit_count_domain",
    "digit_count_subdomain",
    "digit_count_path",
    "subdomain_count",
    "random_domain",
    "length_domain",
    "length_subdomain",
    "length_path",
    "known_tld",
    "www_in_domain_subdomain",
    "com_in_domain_subdomain",
    "punycode",
    "count_hyphen",
    "count_dot",
    "count_slash",
    "count_at",
    "count_question",
    "count_ampersand",
    "count_equal",
    "count_underscore",
    "consecutive_character_repeat",
    "uses_https",
    "host_is_ip",
)


def _fingerprint():
    digest = hashlib.sha256()
    digest.update(FEATURE_SCHEMA_VERSION.encode() + b"\0" + tldextract.__version__.encode() + b"\0")
    digest.update(
        hashlib.sha256(
            resources.files("tldextract").joinpath(".tld_set_snapshot").read_bytes()
        ).digest()
    )
    for path in sorted(RESOURCE_DIR.iterdir()):
        if path.is_file() and not path.name.startswith("."):
            digest.update(path.name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


RESOURCE_FINGERPRINT = _fingerprint()


class FeatureExtractor:
    """Pure URL-string analysis with stable feature order and finite float values.

    Domain digits/length use the main registrable label, excluding suffix; path
    includes query and excludes fragment. Raw tokens omit scheme/fragment. Special
    character/repeat counts use the full normalized URL. No feature grants trust.
    """

    def extract(self, url: str) -> dict[str, float]:
        parsed = parse_url(url)
        raw = raw_tokens(parsed.hostname + parsed.path_query)
        lengths = [len(x) for x in raw]
        decomposed = [(letters_only(word), decompose(word)) for word in raw]
        compounds = [(word, parts) for word, parts in decomposed if len(parts) > 1]
        all_words = tuple(part for _, parts in decomposed for part in parts)
        random_words = tuple(word for word in all_words if is_random_word(word))
        words = tuple(word for word in all_words if not is_random_word(word))
        target = tuple(
            part
            for word in raw_tokens(parsed.domain_label)
            for part in decompose(word)
            if not is_random_word(part)
        )
        labels = (
            []
            if parsed.is_ip
            else (
                [*parsed.subdomain.split("."), parsed.domain_label]
                if parsed.subdomain
                else [parsed.domain_label]
            )
        )
        full = parsed.normalized
        values = (
            len(raw),
            int(parsed.registered_domain in OFFICIAL_DOMAINS),
            statistics.mean(lengths) if lengths else 0,
            max(lengths, default=0),
            min(lengths, default=0),
            statistics.pstdev(lengths) if lengths else 0,
            len(compounds),
            statistics.mean([len(word) for word, _ in compounds]) if compounds else 0,
            sum(len(parts) for _, parts in compounds),
            sum(word in KEYWORDS for word in words),
            sum(word in BRANDS for word in words),
            sum(bool(similar_matches(word, KEYWORDS)) for word in words),
            sum(bool(similar_matches(word, BRANDS)) for word in words),
            len(random_words),
            sum(word in BRANDS for word in target),
            sum(word in KEYWORDS for word in target),
            sum(
                word in DICTIONARY and word not in KEYWORDS and word not in BRANDS for word in words
            ),
            sum(x.isascii() and x.isdigit() for x in parsed.domain_label),
            sum(x.isascii() and x.isdigit() for x in parsed.subdomain),
            sum(x.isascii() and x.isdigit() for x in parsed.path_query),
            len(parsed.subdomain.split(".")) if parsed.subdomain else 0,
            int(not parsed.is_ip and is_random_word(parsed.domain_label)),
            len(parsed.domain_label),
            len(parsed.subdomain),
            len(parsed.path_query),
            int(
                bool(parsed.suffix)
                and (parsed.suffix in KNOWN_TLDS or parsed.suffix.rsplit(".", 1)[-1] in KNOWN_TLDS)
            ),
            labels.count("www"),
            labels.count("com"),
            int(any(x.startswith("xn--") for x in parsed.hostname.split("."))),
            *(full.count(x) for x in "-./@?&=_"),
            sum(a == b and a.isalnum() for a, b in zip(full, full[1:])),
            int(urlsplit(full).scheme == "https"),
            int(parsed.is_ip),
        )
        if len(values) != len(FEATURE_NAMES):
            raise RuntimeError("Feature schema mismatch")
        result = dict(zip(FEATURE_NAMES, map(float, values)))
        if not all(math.isfinite(value) for value in result.values()):
            raise RuntimeError("Non-finite feature")
        return result

    def vector(self, url: str) -> list[float]:
        features = self.extract(url)
        return [features[name] for name in FEATURE_NAMES]

    def explain(self, url: str) -> list[str]:
        """Observed indicators only, not RF contribution or causality explanations."""
        parsed = parse_url(url)
        values = self.extract(parsed.normalized)
        reasons = []
        for key, message in [
            ("host_is_ip", "도메인 이름 대신 IP 주소를 사용해요."),
            ("punycode", "국제화 도메인(Punycode) 문자열이 포함되어 있어요."),
            ("keyword_count", "로컬 목록의 계정·인증·배송 관련 단어가 포함되어 있어요."),
            (
                "brand_name_count",
                "로컬 브랜드 목록과 일치하는 단어가 있어요. 소유권을 확인한 것은 아니에요.",
            ),
            ("similar_keyword_count", "편집 거리 기준으로 키워드와 유사한 단어가 있어요."),
            ("similar_brand_name_count", "편집 거리 기준으로 브랜드 이름과 유사한 단어가 있어요."),
            ("random_word_count", "실험용 문자쌍 모델에서 낮은 점수를 받은 단어가 있어요."),
        ]:
            if values[key]:
                reasons.append(message)
        if not values["uses_https"]:
            reasons.insert(0, "HTTPS가 아닌 HTTP URL이에요.")
        if "-" in parsed.hostname:
            reasons.append("호스트 이름에 하이픈이 포함되어 있어요.")
        if values["digit_count_domain"] + values["digit_count_subdomain"]:
            reasons.append("호스트 이름에 숫자가 포함되어 있어요.")
        if len(parsed.normalized) > 80:
            reasons.append("정규화한 URL이 80자보다 길어요.")
        if values["subdomain_count"] >= 3:
            reasons.append("등록 도메인 앞에 하위 도메인이 3개 이상 있어요.")
        return reasons[:12] or [
            "URL 문자열의 40개 특징을 분석했어요. 사이트 내용과 평판은 조회하지 않았어요."
        ]
