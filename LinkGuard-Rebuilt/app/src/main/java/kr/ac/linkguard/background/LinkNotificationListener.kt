package kr.ac.linkguard.background
import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kr.ac.linkguard.LinkGuardApplication
import kr.ac.linkguard.core.ScanSource
class LinkNotificationListener : NotificationListenerService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val queue = Channel<String>(16)
    override fun onCreate() {
        super.onCreate()
        scope.launch { for (text in queue) { try { UrlIntake.process(applicationContext, text, ScanSource.NOTIFICATION) } catch (e: CancellationException) { throw e } catch (_: Exception) { AlertNotifier.notifyFailure(applicationContext) } } }
    }
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val settings = (application as LinkGuardApplication).repository.settings.value
        if (!settings.protectionEnabled || !settings.notificationEnabled || !PermissionHelper.notificationAccessGranted(this)) return
        if (sbn.packageName == packageName || sbn.isOngoing || sbn.notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return
        val extras = sbn.notification.extras ?: return
        val text = buildString {
            for (key in listOf(Notification.EXTRA_TITLE, Notification.EXTRA_TEXT, Notification.EXTRA_BIG_TEXT)) {
                if (length >= 16_384) break
                extras.getCharSequence(key)?.let { append(it.take(16_384 - length)); append(' ') }
            }
            extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)?.take(20)?.forEach { if (length < 16_384) { append(it.take(16_384 - length)); append(' ') } }
        }.take(16_384)
        if (text.isNotBlank()) queue.trySend(text)
    }
    override fun onDestroy() { queue.close(); scope.cancel(); super.onDestroy() }
}
