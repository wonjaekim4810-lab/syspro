package kr.ac.linkguard.core

enum class RiskLevel { LOW, CAUTION, HIGH }
enum class ScanSource(val label: String) { MANUAL("직접 검사"), QR("QR 코드"), SMS("SMS"), NOTIFICATION("앱 알림"), SHARE("공유 링크") }
enum class AnalysisMode { LOCAL_RULES, REMOTE_AI }
data class ScanResult(val id: String, val timestamp: Long, val originalUrl: String, val normalizedUrl: String, val score: Int, val level: RiskLevel, val reasons: List<String>, val source: ScanSource, val mode: AnalysisMode, val modelVersion: String? = null)
