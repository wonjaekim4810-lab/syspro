"""Show intermediate algorithm values without requiring or inventing a classifier."""

import argparse, json
from dataclasses import asdict
from linkguard.urltools import parse_url
from linkguard.features import FeatureExtractor, FEATURE_SCHEMA_VERSION
from linkguard.nlp import (
    raw_tokens,
    decompose,
    bigram_score,
    is_random_word,
    similar_matches,
    BRANDS,
    KEYWORDS,
)


def explain_url(url):
    parsed = parse_url(url)
    words = raw_tokens(parsed.hostname + parsed.path_query)
    steps = []
    for raw in words:
        segments = decompose(raw)
        steps.append(
            {
                "raw": raw,
                "wdm": list(segments),
                "segments": [
                    {
                        "word": word,
                        "bigram_score": bigram_score(word),
                        "random": is_random_word(word),
                        "similar_brands": list(similar_matches(word, BRANDS)),
                        "similar_keywords": list(similar_matches(word, KEYWORDS)),
                        "used_by_mam": not is_random_word(word),
                    }
                    for word in segments
                ],
            }
        )
    return {
        "normalized_url": parsed.normalized,
        "parts": asdict(parsed),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "raw_tokens": list(words),
        "steps": steps,
        "features": FeatureExtractor().extract(url),
        "observations": FeatureExtractor().explain(url),
        "notice": "중간 특징 설명이며 모델의 피싱 판정이 아닙니다.",
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("url")
    args = p.parse_args(argv)
    print(json.dumps(explain_url(args.url), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
