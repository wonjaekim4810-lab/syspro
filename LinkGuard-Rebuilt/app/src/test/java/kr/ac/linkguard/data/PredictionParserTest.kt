package kr.ac.linkguard.data
import kr.ac.linkguard.core.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
class PredictionParserTest {
    private fun body(): JSONObject = JSONObject().put("url", "https://example.com").put("status", "safe").put("score", 18).put("reasons", listOf("관찰 특징")).put("model_version", "rf-test")
    private fun parse(text: String) = PredictionParser.parse(text, "example.com", "https://example.com", ScanSource.MANUAL)
    @Test fun validatesRealContractAndKeepsServerGrade() {
        val r = parse(body().put("status", "danger").put("score", 1).toString())
        assertEquals(RiskLevel.HIGH, r.level); assertEquals(1, r.score); assertEquals(AnalysisMode.REMOTE_AI, r.mode); assertEquals("rf-test", r.modelVersion)
    }
    @Test fun rejectsWrongUrlAndUnknownStatus() {
        assertTrue(runCatching { parse(body().put("url", "https://elsewhere.example").toString()) }.isFailure)
        assertTrue(runCatching { parse(body().put("status", "unknown").toString()) }.isFailure)
    }
    @Test fun rejectsNonIntegerScoresAndOutOfRange() {
        listOf<Any>("18", true, 18.5, -1, 101).forEach { assertTrue(runCatching { parse(body().put("score", it).toString()) }.isFailure) }
        assertTrue(runCatching { parse(body().toString().replace("\"score\":18", "\"score\":18.0")) }.isFailure)
    }
    @Test fun rejectsMissingOrUnboundedReasonsAndVersion() {
        for (key in listOf("model_version", "reasons")) { val j = body(); j.remove(key); assertTrue(runCatching { parse(j.toString()) }.isFailure) }
        assertTrue(runCatching { parse(body().put("reasons", emptyList<String>()).toString()) }.isFailure)
        assertTrue(runCatching { parse(body().put("model_version", "x".repeat(121)).toString()) }.isFailure)
    }
    @Test fun rejectsNonObjectsAndTrailingGarbage() { for (text in listOf("[]", "null", "not json", body().toString() + "trailing")) assertTrue(runCatching { parse(text) }.isFailure) }
}
