package kr.ac.linkguard.core

import java.net.URI
import java.util.UUID

/** Illustrative local structure rules, not a trained AI classifier. */
class RuleAnalyzer {
    fun analyze(input: String, source: ScanSource = ScanSource.MANUAL): ScanResult {
        val normalized = UrlTools.normalize(input)
        val uri = URI(normalized)
        val authority = uri.rawAuthority
        val host = if (authority.startsWith('[')) authority.substringAfter('[').substringBefore(']') else authority.substringBefore(':')
        val searchable = (host + uri.rawPath.orEmpty() + uri.rawQuery.orEmpty()).lowercase()
        var score = 7
        val reasons = mutableListOf<String>()
        fun add(points: Int, reason: String) { score += points; reasons += reason }
        if (uri.scheme == "http") add(23, "HTTPS가 아닌 HTTP 형식이에요.")
        if (UrlTools.isIpv4(host) || host.contains(':')) add(26, "도메인 이름 대신 IP 주소를 사용해요.")
        if (host.split('.').any { it.startsWith("xn--") }) add(17, "국제화 도메인(Punycode)을 사용해요.")
        if ('-' in host) add(13, "호스트 이름에 하이픈이 포함되어 있어요.")
        if (Regex("login|verify|update|confirm|account|secure|password|delivery|parcel").containsMatchIn(searchable)) add(19, "인증·계정·배송 관련 문자열이 포함되어 있어요.")
        if (normalized.length > 80) add(12, "URL이 80자보다 길어요.")
        if (host.removePrefix("www.") in setOf("bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly")) add(17, "단축 URL 형태예요. 최종 목적지는 확인하지 않았어요.")
        if (host.any { it.isDigit() }) add(7, "호스트 이름에 숫자가 포함되어 있어요.")
        if (reasons.isEmpty()) reasons += "로컬 규칙에서 두드러지는 의심 패턴을 찾지 못했어요."
        score = score.coerceAtMost(99)
        return ScanResult(UUID.randomUUID().toString(), System.currentTimeMillis(), input.trim(), normalized, score, levelForScore(score), reasons, source, AnalysisMode.LOCAL_RULES)
    }
    companion object {
        fun levelForScore(score: Int): RiskLevel = when { score >= 65 -> RiskLevel.HIGH; score >= 32 -> RiskLevel.CAUTION; else -> RiskLevel.LOW }
    }
}
