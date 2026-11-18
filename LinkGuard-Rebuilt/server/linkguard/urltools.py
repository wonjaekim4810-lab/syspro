"""Rebuilt HTTP(S) parser and offline registrable-domain grouping.

This module never resolves DNS, opens the inspected URL or downloads a suffix list.
The normalization examples and UTF-16 length limit match the Kotlin client contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import ipaddress
import re
from urllib.parse import urlsplit

import tldextract

MAX_URL_LENGTH = 4096
_HTTP = re.compile(r"^https?://", re.I)
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
_HOST_PORT = re.compile(r"^[^/:?#]+\.[^/:?#]+:[0-9]+(?:[/?#]|$)")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
_SUFFIXES = tldextract.TLDExtract(
    cache_dir=None, suffix_list_urls=(), include_psl_private_domains=True
)


class URLValidationError(ValueError):
    """The input is not an accepted HTTP(S) URL."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise URLValidationError(message)


def _utf16_units(value: str) -> int:
    try:
        return len(value.encode("utf-16-le")) // 2
    except UnicodeEncodeError:
        raise URLValidationError("Unpaired Unicode surrogate is not permitted") from None


def _authority(value: str) -> tuple[str, str, bool]:
    _require(bool(value) and "@" not in value, "Missing host or credentials are not supported")
    if value.startswith("["):
        end = value.find("]")
        _require(end > 1, "Malformed IPv6 literal")
        host, port = value[1:end], value[end + 1 :]
        _require(
            bool(re.fullmatch(r"[0-9a-fA-F:.]+", host)) and ":" in host, "Malformed IPv6 literal"
        )
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            raise URLValidationError("Malformed IPv6 literal") from None
        host, ipv6 = host.lower(), True
    else:
        _require(value.count(":") <= 1, "IPv6 addresses require square brackets")
        host, sep, tail = value.rpartition(":")
        if not sep:
            host, port = value, ""
        else:
            port = ":" + tail
        try:
            host = host.encode("idna").decode("ascii").lower().removesuffix(".")
        except (UnicodeError, ValueError):
            raise URLValidationError("Malformed domain") from None
        labels = host.split(".")
        _require(
            len(host) <= 253 and len(labels) >= 2 and all(_LABEL.fullmatch(x) for x in labels),
            "Malformed domain",
        )
        if re.fullmatch(r"[0-9.]+", host):
            try:
                ipaddress.IPv4Address(host)
            except ValueError:
                raise URLValidationError("Malformed IPv4 literal") from None
        ipv6 = False
    _require(
        not port or bool(re.fullmatch(r":[0-9]{1,5}", port)) and 1 <= int(port[1:]) <= 65535,
        "Port must be between 1 and 65535",
    )
    return host, port, ipv6


def normalize_url(value: str) -> str:
    """Default to HTTPS, normalize host, and preserve path/query/fragment spelling."""
    _require(isinstance(value, str), "URL must be a string")
    _require(_utf16_units(value) <= MAX_URL_LENGTH, "URL exceeds 4096 UTF-16 units")
    _require(
        not any(ord(x) < 32 or ord(x) == 127 for x in value), "Control characters are not permitted"
    )
    text = value.strip()
    _require(bool(text), "URL is empty")
    _require(
        not any(x.isspace() or x == "\\" for x in text),
        "Whitespace or backslashes are not permitted",
    )
    _require(not any(x in '<>"{}|^`' for x in text), "Invalid URI character")
    _require(not _BAD_PERCENT.search(text), "Malformed percent escape")
    explicit = bool(_HTTP.match(text))
    _require(
        not text.startswith("//")
        and (
            explicit
            or not _SCHEME.match(text)
            or bool(_HOST_PORT.match(text))
            or text.startswith("[")
        ),
        "Only HTTP(S) URLs are supported",
    )
    candidate = text if explicit else "https://" + text
    try:
        parts = urlsplit(candidate)
    except (ValueError, UnicodeError):
        raise URLValidationError("Malformed URL") from None
    _require(parts.scheme.lower() in ("http", "https"), "Only HTTP(S) URLs are supported")
    host, port, ipv6 = _authority(parts.netloc)
    _require(not parts.path or parts.path.startswith("/"), "Malformed path")
    _require(
        "[" not in parts.path and "]" not in parts.path and "#" not in parts.fragment,
        "Malformed path or fragment",
    )
    prefix, fragment_sep, _ = candidate.partition("#")
    result = parts.scheme.lower() + "://" + ("[" + host + "]" if ipv6 else host) + port + parts.path
    if "?" in prefix:
        result += "?" + parts.query
    if fragment_sep:
        result += "#" + parts.fragment
    _require(_utf16_units(result) <= MAX_URL_LENGTH, "Normalized URL exceeds 4096 UTF-16 units")
    return result


@dataclass(frozen=True)
class ParsedURL:
    normalized: str
    hostname: str
    registered_domain: str
    domain_label: str
    suffix: str
    subdomain: str
    path_query: str
    is_ip: bool


@lru_cache(maxsize=8192)
def _domain_parts(host: str) -> tuple[str, str, str, str, bool]:
    try:
        canonical = str(ipaddress.ip_address(host))
    except ValueError:
        pass
    else:
        return canonical, host, "", "", True
    result = _SUFFIXES(host)
    labels = host.split(".")
    if result.suffix and result.domain:
        return (
            result.domain + "." + result.suffix,
            result.domain,
            result.suffix,
            result.subdomain,
            False,
        )
    if result.suffix:
        return host, labels[0], result.suffix, "", False
    return ".".join(labels[-2:]), labels[-2], labels[-1], ".".join(labels[:-2]), False


def parse_url(value: str) -> ParsedURL:
    normalized = normalize_url(value)
    parts = urlsplit(normalized)
    host = (
        parts.netloc[1 : parts.netloc.index("]")]
        if parts.netloc.startswith("[")
        else parts.netloc.split(":", 1)[0]
    )
    registered, label, suffix, subdomain, is_ip = _domain_parts(host)
    path_query = parts.path + ("?" + parts.query if "?" in normalized.partition("#")[0] else "")
    return ParsedURL(normalized, host, registered, label, suffix, subdomain, path_query, is_ip)


def domain_group(value: str) -> str:
    """Offline registered-domain group used to prevent domain overlap at evaluation."""
    return parse_url(value).registered_domain
