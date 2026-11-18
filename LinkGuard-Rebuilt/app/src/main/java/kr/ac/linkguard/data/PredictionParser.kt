package kr.ac.linkguard.data

import kr.ac.linkguard.core.*
import org.json.JSONObject
import org.json.JSONTokener
import java.util.UUID

internal object PredictionParser {
    fun parse(body: String, original: String, normalized: String, source: ScanSource): ScanResult {
        try {
            val tokener = JSONTokener(body)
            val json = tokener.nextValue() as? JSONObject ?: error("object")
            require(tokener.nextClean() == '\u0000')
            require(UrlTools.normalize(json.get("url") as? String ?: error("url")) == normalized)
            val level = when (json.get("status")) { "safe" -> RiskLevel.LOW; "caution" -> RiskLevel.CAUTION; "danger" -> RiskLevel.HIGH; else -> error("status") }
            val score = when (val raw = json.get("score")) { is Int -> raw; is Long -> raw.also { require(it in 0L..100L) }.toInt(); else -> error("integer") }.also { require(it in 0..100) }
            val array = json.getJSONArray("reasons"); require(array.length() in 1..12)
            val reasons = (0 until array.length()).map { (array.get(it) as? String ?: error("reason")).trim().also { text -> require(text.isNotBlank() && text.length <= 500) } }
            val version = (json.get("model_version") as? String ?: error("version")).trim()
            require(version.isNotBlank() && version.length <= 120 && version.none { it.code < 32 || it.code == 127 })
            return ScanResult(UUID.randomUUID().toString(), System.currentTimeMillis(), original, normalized, score, level, reasons, source, AnalysisMode.REMOTE_AI, version)
        } catch (e: Exception) { throw IllegalStateException("AI 서버 응답이 연동 규격과 맞지 않아요.", e) }
    }
}
