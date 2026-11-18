package kr.ac.linkguard.core
import org.junit.Assert.*
import org.junit.Test
class RuleAnalyzerTest {
    private val analyzer = RuleAnalyzer()
    @Test fun localProvenanceAndLowSignalDoNotClaimAi() {
        val result = analyzer.analyze("https://example.com", ScanSource.QR)
        assertEquals(AnalysisMode.LOCAL_RULES, result.mode); assertEquals(ScanSource.QR, result.source); assertEquals(RiskLevel.LOW, result.level); assertNotNull(result.id); assertTrue(result.reasons.isNotEmpty())
    }
    @Test fun riskyStructureProducesObservableReasons() {
        val result = analyzer.analyze("http://parcel-delivery-verify.example/login")
        assertEquals(RiskLevel.CAUTION, result.level); assertTrue(result.reasons.any { "HTTP" in it }); assertTrue(result.reasons.size >= 3)
        assertEquals(RiskLevel.HIGH, analyzer.analyze("http://192.0.2.10/verify").level)
    }
    @Test fun scoreBoundariesAreExplicitDemoRules() {
        assertEquals(RiskLevel.LOW, RuleAnalyzer.levelForScore(31)); assertEquals(RiskLevel.CAUTION, RuleAnalyzer.levelForScore(32)); assertEquals(RiskLevel.CAUTION, RuleAnalyzer.levelForScore(64)); assertEquals(RiskLevel.HIGH, RuleAnalyzer.levelForScore(65))
    }
    @Test fun shortenerMatchesExactHostNotSubstring() {
        assertTrue(analyzer.analyze("https://bit.ly/a").reasons.any { "단축" in it })
        assertFalse(analyzer.analyze("https://notbit.ly.example/a").reasons.any { "단축" in it })
    }
    @Test fun numericLeadingDomainLabelCannotCrashUriHostParsing() { assertEquals("https://foo.1a", analyzer.analyze("https://foo.1a").normalizedUrl) }
}
