package kr.ac.linkguard.data

import android.content.Context
import kr.ac.linkguard.core.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

data class AppSettings(val protectionEnabled: Boolean = false, val smsEnabled: Boolean = false, val notificationEnabled: Boolean = false, val warningEnabled: Boolean = true, val remoteEnabled: Boolean = false, val serverUrl: String = "")

class LinkGuardRepository(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("linkguard_private", Context.MODE_PRIVATE)
    private val lock = Any()
    private val mutableHistory = MutableStateFlow(readHistory())
    val history: StateFlow<List<ScanResult>> = mutableHistory.asStateFlow()
    private val mutableSettings = MutableStateFlow(readSettings())
    val settings: StateFlow<AppSettings> = mutableSettings.asStateFlow()
    fun updateSettings(transform: (AppSettings) -> AppSettings) = synchronized(lock) {
        val next = transform(mutableSettings.value)
        require(next.serverUrl.length <= 2048) { "서버 주소가 너무 길어요." }
        if (next.serverUrl.isNotBlank()) validateBase(next.serverUrl)
        require(!next.remoteEnabled || next.serverUrl.isNotBlank()) { "먼저 서버 주소를 저장해 주세요." }
        prefs.edit().putString("settings", JSONObject().apply {
            put("protectionEnabled", next.protectionEnabled); put("smsEnabled", next.smsEnabled); put("notificationEnabled", next.notificationEnabled)
            put("warningEnabled", next.warningEnabled); put("remoteEnabled", next.remoteEnabled); put("serverUrl", next.serverUrl)
        }.toString()).apply()
        mutableSettings.value = next
    }
    suspend fun analyze(input: String, source: ScanSource = ScanSource.MANUAL): ScanResult = withContext(Dispatchers.IO) {
        val normalized = UrlTools.normalize(input)
        val config = settings.value
        val result = if (config.remoteEnabled) remote(input.trim(), normalized, source, config.serverUrl) else RuleAnalyzer().analyze(input, source)
        currentCoroutineContext().ensureActive()
        synchronized(lock) {
            mutableHistory.value = (listOf(result) + mutableHistory.value).take(200)
            persistHistory()
        }
        result
    }
    fun clearHistory() = synchronized(lock) { mutableHistory.value = emptyList(); prefs.edit().remove("history").apply() }
    fun findResult(id: String): ScanResult? = history.value.firstOrNull { it.id == id }
    private fun persistHistory() {
        val array = JSONArray()
        history.value.forEach { r -> array.put(JSONObject().apply {
            put("id", r.id); put("timestamp", r.timestamp); put("originalUrl", r.originalUrl); put("normalizedUrl", r.normalizedUrl)
            put("score", r.score); put("level", r.level.name); put("reasons", JSONArray(r.reasons)); put("source", r.source.name); put("mode", r.mode.name)
            r.modelVersion?.let { put("modelVersion", it) }
        }) }
        prefs.edit().putString("history", array.toString()).apply()
    }
    private fun readSettings(): AppSettings = runCatching {
        val j = JSONObject(prefs.getString("settings", "{}") ?: "{}")
        AppSettings(j.optBoolean("protectionEnabled"), j.optBoolean("smsEnabled"), j.optBoolean("notificationEnabled"), j.optBoolean("warningEnabled", true), j.optBoolean("remoteEnabled"), j.optString("serverUrl").take(2048))
    }.getOrDefault(AppSettings())
    private fun readHistory(): List<ScanResult> = runCatching {
        val a = JSONArray(prefs.getString("history", "[]") ?: "[]")
        (0 until minOf(a.length(), 200)).mapNotNull { i -> runCatching {
            val j = a.getJSONObject(i); val r = j.getJSONArray("reasons")
            ScanResult(j.getString("id"), j.getLong("timestamp"), j.getString("originalUrl"), j.getString("normalizedUrl"), j.getInt("score").also { require(it in 0..100) }, RiskLevel.valueOf(j.getString("level")), (0 until r.length()).map { r.getString(it) }, ScanSource.valueOf(j.getString("source")), AnalysisMode.valueOf(j.getString("mode")), if (j.has("modelVersion")) j.getString("modelVersion") else null)
        }.getOrNull() }
    }.getOrDefault(emptyList())
    private fun validateBase(value: String): String {
        val normalized = UrlTools.normalize(value.trim()); val uri = URI(normalized)
        require(uri.scheme == "https" && uri.rawQuery == null && uri.rawFragment == null) { "쿼리·프래그먼트 없는 HTTPS 서버 주소를 입력해 주세요." }
        return normalized.trimEnd('/')
    }
    private fun remote(original: String, normalized: String, source: ScanSource, base: String): ScanResult {
        val connection = URL(validateBase(base) + "/predict").openConnection() as HttpURLConnection
        connection.apply { requestMethod = "POST"; connectTimeout = 10_000; readTimeout = 15_000; instanceFollowRedirects = false; doOutput = true; setRequestProperty("Content-Type", "application/json; charset=utf-8"); setRequestProperty("Accept", "application/json") }
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(25)
        val watchdog = scheduler.schedule({ connection.disconnect() }, 25, TimeUnit.SECONDS)
        fun timeout(): Int {
            val remaining = TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime())
            if (remaining <= 0) throw java.net.SocketTimeoutException()
            return remaining.coerceAtMost(15_000).toInt().coerceAtLeast(1)
        }
        try {
            val request = JSONObject().put("url", normalized).toString().toByteArray(Charsets.UTF_8)
            connection.setFixedLengthStreamingMode(request.size); connection.outputStream.use { it.write(request) }; connection.readTimeout = timeout()
            when (val code = connection.responseCode) {
                200 -> Unit
                400, 422 -> error("AI 서버가 URL 입력을 거부했어요.")
                503 -> error("AI 서버에 학습된 모델이 준비되지 않았거나 요청이 많아요.")
                401, 403 -> error("AI 서버 접근 권한을 확인해 주세요.")
                in 300..399 -> error("서버 주소가 이동했어요. 설정을 확인해 주세요.")
                else -> error("AI 서버 오류가 발생했어요. (HTTP $code)")
            }
            require(connection.contentType.orEmpty().substringBefore(';').trim().equals("application/json", true)) { "AI 서버 응답이 JSON이 아니에요." }
            val response = connection.inputStream.use { stream ->
                val out = ByteArrayOutputStream(); val buffer = ByteArray(4096)
                while (true) { connection.readTimeout = timeout(); val count = stream.read(buffer); if (count < 0) break; require(out.size() + count <= 65536) { "서버 응답이 너무 커요." }; out.write(buffer, 0, count) }
                out.toByteArray().toString(Charsets.UTF_8)
            }
            return PredictionParser.parse(response, original, normalized, source)
        } catch (e: java.net.SocketTimeoutException) { throw IllegalStateException("AI 서버 응답 시간이 초과됐어요.", e)
        } catch (e: javax.net.ssl.SSLException) { throw IllegalStateException("AI 서버 HTTPS 인증서를 확인할 수 없어요.", e)
        } catch (e: IOException) { throw IllegalStateException("AI 서버 연결을 확인해 주세요.", e)
        } finally { watchdog.cancel(false); connection.disconnect() }
    }
    companion object { private val scheduler = Executors.newSingleThreadScheduledExecutor { r -> Thread(r, "linkguard-request-deadline").apply { isDaemon = true } } }
}
