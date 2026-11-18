package kr.ac.linkguard.background
import android.content.Context
import android.os.SystemClock
import kotlinx.coroutines.CancellationException
import kr.ac.linkguard.LinkGuardApplication
import kr.ac.linkguard.core.*
import java.security.MessageDigest
internal object UrlIntake {
    private val recent = LinkedHashMap<String, Long>()
    private fun reserve(url: String): Boolean = synchronized(recent) {
        val now = SystemClock.elapsedRealtime()
        recent.entries.removeAll { now - it.value >= 60_000 }
        val key = MessageDigest.getInstance("SHA-256").digest(url.toByteArray()).joinToString("") { "%02x".format(it) }
        if (key in recent) return@synchronized false
        while (recent.size >= 256) recent.remove(recent.keys.first())
        recent[key] = now; true
    }
    suspend fun process(context: Context, text: String, source: ScanSource) {
        val repository = (context.applicationContext as LinkGuardApplication).repository
        for (url in UrlTools.extract(text.take(16_384)).take(3)) {
            val config = repository.settings.value
            if (!config.protectionEnabled) return
            if (source == ScanSource.SMS && (!config.smsEnabled || !PermissionHelper.smsGranted(context))) return
            if (source == ScanSource.NOTIFICATION && (!config.notificationEnabled || !PermissionHelper.notificationAccessGranted(context))) return
            if (!reserve(url)) continue
            try { AlertNotifier.notifyResult(context, repository.analyze(url, source)) }
            catch (e: CancellationException) { throw e }
            catch (_: Exception) { AlertNotifier.notifyFailure(context) }
        }
    }
}
