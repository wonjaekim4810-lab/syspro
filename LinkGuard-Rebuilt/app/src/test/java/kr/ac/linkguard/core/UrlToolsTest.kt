package kr.ac.linkguard.core
import org.junit.Assert.*
import org.junit.Test
class UrlToolsTest {
    @Test fun normalizedHostRetainsPathQueryFragment() {
        assertEquals("https://example.com/Path?q=A%2FB#f", UrlTools.normalize(" EXAMPLE.com/Path?q=A%2FB#f "))
        assertEquals("http://example.com:8080/a", UrlTools.normalize("HTTP://Example.com:8080/a"))
        assertEquals("https://example.com?#", UrlTools.normalize("example.com?#"))
    }
    @Test fun idnAndNumericLiterals() {
        assertEquals("https://xn--bcher-kva.de", UrlTools.normalize("https://bücher.de"))
        assertEquals("https://[2001:db8::1]:443/a", UrlTools.normalize("https://[2001:DB8::1]:443/a"))
        assertEquals("https://192.0.2.10", UrlTools.normalize("192.0.2.10"))
    }
    @Test fun rejectsUnsafeMalformedAndOverlongInput() {
        listOf("javascript:alert(1)", "ftp://example.com", "//example.com", "https:example.com", "https://a:b@example.com", "https://example.com\\@evil.example", "https://example.com\n", "https://bad..example", "https://999.1.1.1", "https://01.2.3.4", "https://localhost", "https://example.com:0", "https://example.com:65536", "https://[2001:::1]", "https://example.com/%gg", "https://example.com/" + "x".repeat(4096)).forEach { assertTrue(it, runCatching { UrlTools.normalize(it) }.isFailure) }
    }
    @Test fun extractsOnlyExplicitValidatedUniqueUrls() {
        assertEquals(listOf("https://example.com/a", "http://example.org?q=1"), UrlTools.extract("주소 (https://example.com/a), https://example.com/a HTTP://example.org?q=1. https://bad..example"))
        assertTrue(UrlTools.extract("example.com").isEmpty())
        assertEquals(20, UrlTools.extract((1..25).joinToString(" ") { "https://example.com/$it" }).size)
    }
    @Test fun utf16LimitAndSurrogatesMatchServerConstraints() {
        val good = "https://example.com/" + "😀".repeat(100)
        assertEquals(good, UrlTools.normalize(good))
        assertTrue(runCatching { UrlTools.normalize("https://example.com/" + "😀".repeat(2100)) }.isFailure)
        assertTrue(runCatching { UrlTools.normalize("https://example.com/" + '\uD800') }.isFailure)
    }
    @Test fun balancedParenthesesAndIpv6Preserved() {
        assertEquals(listOf("https://[2001:db8::1]", "https://example.com/a(b)"), UrlTools.extract("[https://[2001:db8::1]] (https://example.com/a(b))"))
    }
}
