"""Read-only normalization, Kotlin-contract and offline PSL behavior checks."""

import socket
import unittest
from unittest.mock import patch

from linkguard.urltools import URLValidationError, domain_group, normalize_url, parse_url


class URLToolsTests(unittest.TestCase):
    def test_normalization_preserves_application_components(self):
        cases = {
            " EXAMPLE.com/Path?q=A%2FB#frag ": "https://example.com/Path?q=A%2FB#frag",
            "HTTP://Example.com:8080/a": "http://example.com:8080/a",
            "example.com:443/a": "https://example.com:443/a",
            "https://bücher.de/path": "https://xn--bcher-kva.de/path",
            "https://example.com/?#": "https://example.com/?#",
            "https://example.com:00443/a": "https://example.com:00443/a",
        }
        for given, expected in cases.items():
            with self.subTest(given=given):
                self.assertEqual(normalize_url(given), expected)
                self.assertEqual(normalize_url(expected), expected)

    def test_ip_literals_preserve_spelling_but_group_canonically(self):
        self.assertEqual(normalize_url("192.0.2.10/verify"), "https://192.0.2.10/verify")
        self.assertEqual(
            normalize_url("https://[2001:DB8::1]:443/a"), "https://[2001:db8::1]:443/a"
        )
        self.assertEqual(normalize_url("https://[::ffff:192.0.2.1]"), "https://[::ffff:192.0.2.1]")
        self.assertEqual(
            domain_group("https://[2001:db8::1]/a"),
            domain_group("http://[2001:0db8:0:0:0:0:0:1]/b"),
        )

    def test_rejects_malformed_schemes_credentials_hosts_ports_and_escapes(self):
        invalid = [
            "javascript:alert(1)",
            "ftp://example.com",
            "https:example.com",
            "//example.com",
            "https://user:pass@example.com",
            "https://exa mple.com",
            "https://example.com\\@evil.com",
            "https://example.com\n",
            "https://example..com",
            "https://999.1.1.1",
            "https://01.2.3.4",
            "https://localhost",
            "https://example.com:0",
            "https://example.com:65536",
            "https://example.com:abc",
            "https://[2001:::1]",
            "https://[invalid]",
            "https://-bad.example",
            "https://example.com/%zz",
            "https://example.com/a[b]",
            "https://example.com/#first#second",
            "https://example.com/<tag>",
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(URLValidationError):
                normalize_url(value)

    def test_utf16_limit_and_surrogates_match_android_length_semantics(self):
        prefix = "https://example.com/"
        limit = prefix + "a" * (4096 - len(prefix))
        self.assertEqual(normalize_url(limit), limit)
        for value in [
            limit + "a",
            prefix + "😀" * 2100,
            prefix + "\ud800",
            prefix + "\udfff",
            None,
            123,
        ]:
            with self.subTest(kind=type(value).__name__), self.assertRaises(URLValidationError):
                normalize_url(value)
        accepted = prefix + "😀" * ((4096 - len(prefix)) // 2)
        self.assertEqual(normalize_url(accepted), accepted)

    def test_parsed_partitions_include_query_exclude_fragment(self):
        parsed = parse_url("https://a.b.example.co.uk/p1?q=2#f3")
        self.assertEqual(parsed.registered_domain, "example.co.uk")
        self.assertEqual(parsed.domain_label, "example")
        self.assertEqual(parsed.subdomain, "a.b")
        self.assertEqual(parsed.suffix, "co.uk")
        self.assertEqual(parsed.path_query, "/p1?q=2")
        self.assertFalse(parsed.is_ip)

    def test_offline_private_suffix_and_unknown_domain_grouping(self):
        self.assertEqual(domain_group("https://a.example.co.kr"), "example.co.kr")
        self.assertEqual(domain_group("https://a.example.co.uk"), "example.co.uk")
        self.assertEqual(domain_group("https://a.project.github.io"), "project.github.io")
        self.assertNotEqual(
            domain_group("https://one.github.io"), domain_group("https://two.github.io")
        )
        self.assertEqual(domain_group("https://a.brand.example"), "brand.example")

    def test_no_dns_connections_or_suffix_downloads(self):
        with patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("No DNS")
        ), patch.object(socket, "create_connection", side_effect=AssertionError("No connection")):
            self.assertEqual(
                domain_group("https://a.uniqueoffline-check.co.uk"), "uniqueoffline-check.co.uk"
            )
            self.assertEqual(domain_group("https://[2001:db8::f]"), "2001:db8::f")


if __name__ == "__main__":
    unittest.main()
