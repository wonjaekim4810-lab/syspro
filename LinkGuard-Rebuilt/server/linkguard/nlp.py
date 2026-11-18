"""Independently rebuilt bounded WDM/RWDM/MAM adaptations.

The small curated lexical data and all numeric cutoffs are experimental project
choices. They are not the paper's original dictionary, corpus or validated rules.
"""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re
from urllib.parse import unquote

RESOURCE_DIR = Path(__file__).with_name("resources")


def _words(name: str) -> frozenset[str]:
    return frozenset(
        line.strip().lower()
        for line in (RESOURCE_DIR / name).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


DICTIONARY = _words("dictionary.txt")
KEYWORDS = _words("keywords.txt")
BRAND_DOMAINS = {
    name: tuple(domains)
    for name, domains in json.loads((RESOURCE_DIR / "brands.json").read_text()).items()
}
BRANDS = frozenset(BRAND_DOMAINS)
OFFICIAL_DOMAINS = frozenset(domain for domains in BRAND_DOMAINS.values() for domain in domains)
KNOWN_TLDS = _words("known_tlds.txt")
LEXICON = DICTIONARY | KEYWORDS | BRANDS
_MAX_WORD_LENGTH = max(map(len, LEXICON))
_ALPHABET = "abcdefghijklmnopqrstuvwxyz "


def letters_only(word: str) -> str:
    return re.sub("[^a-z]", "", word.lower())


def raw_tokens(text: str) -> tuple[str, ...]:
    """Single percent decoding followed by ASCII alphanumeric tokenization."""
    return tuple(re.findall(r"[a-z0-9]+", unquote(text).lower()))


def decompose(word: str) -> tuple[str, ...]:
    """Non-overlap segmentation maximizing known coverage then longest words."""
    token = letters_only(word)
    if not token:
        return ()
    if token in LEXICON or len(token) <= 7 or len(token) > 80:
        return (token,)
    n = len(token)
    dp = [(0, 0, 0, ()) for _ in range(n + 1)]
    for start in range(n - 1, -1, -1):
        best = dp[start + 1]
        for end in range(start + 3, min(n, start + _MAX_WORD_LENGTH) + 1):
            if token[start:end] not in LEXICON:
                continue
            tail, length = dp[end], end - start
            candidate = (
                tail[0] + length,
                tail[1] + length * length,
                tail[2] - 1,
                ((start, end),) + tail[3],
            )
            if candidate[:3] > best[:3]:
                best = candidate
        dp[start] = best
    spans = dp[0][3]
    if len(spans) < 2:
        return (token,)
    result, previous = [], 0
    for start, end in spans:
        if start > previous:
            result.append(token[previous:start])
        result.append(token[start:end])
        previous = end
    if previous < n:
        result.append(token[previous:])
    return tuple(result)


def _learn_bigrams():
    text = (RESOURCE_DIR / "corpus.txt").read_text().lower() + " " + " ".join(sorted(LEXICON))
    pairs, totals = Counter(), Counter()
    for word in re.findall("[a-z]+", text):
        padded = " " + word + " "
        for a, b in zip(padded, padded[1:]):
            pairs[a, b] += 1
            totals[a] += 1
    return pairs, totals


_BIGRAMS, _TOTALS = _learn_bigrams()


def bigram_score(word: str) -> float:
    token = letters_only(word)
    if not token:
        return 0.0
    padded = " " + token + " "
    logs = [
        math.log((_BIGRAMS[a, b] + 0.2) / (_TOTALS[a] + 0.2 * len(_ALPHABET)))
        for a, b in zip(padded, padded[1:])
    ]
    return math.exp(sum(logs) / len(logs))


def is_random_word(word: str) -> bool:
    token = letters_only(word)
    if len(token) < 5 or token in LEXICON:
        return False
    parts = decompose(token)
    if len(parts) > 1 and all(part in LEXICON for part in parts):
        return False
    return bigram_score(token) < 0.025


def bounded_edit_distance(first: str, second: str, maximum: int = 1) -> int:
    if maximum < 0:
        raise ValueError("maximum must be nonnegative")
    if abs(len(first) - len(second)) > maximum:
        return maximum + 1
    if first == second:
        return 0
    if len(first) > len(second):
        first, second = second, first
    previous, sentinel = list(range(len(second) + 1)), maximum + 1
    for i, a in enumerate(first, 1):
        current = [sentinel] * (len(second) + 1)
        current[0] = i
        for j in range(max(1, i - maximum), min(len(second), i + maximum) + 1):
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != second[j - 1])
            )
        if min(current) > maximum:
            return sentinel
        previous = current
    return min(previous[-1], sentinel)


def similar_matches(word: str, targets: frozenset[str]) -> tuple[str, ...]:
    token = letters_only(word)
    if len(token) < 4 or len(token) > 64 or token in targets:
        return ()
    maximum = 2 if len(token) >= 8 else 1
    return tuple(
        target
        for target in sorted(targets)
        if len(target) >= 4 and bounded_edit_distance(token, target, maximum) <= maximum
    )
