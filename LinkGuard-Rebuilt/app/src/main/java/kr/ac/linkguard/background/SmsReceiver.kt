package kr.ac.linkguard.background
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.provider.Telephony
import kotlinx.coroutines.*
import kr.ac.linkguard.LinkGuardApplication
import kr.ac.linkguard.core.ScanSource
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val settings = (context.applicationContext as LinkGuardApplication).repository.settings.value
        if (!settings.protectionEnabled || !settings.smsEnabled || !PermissionHelper.smsGranted(context)) return
        val text = runCatching { Telephony.Sms.Intents.getMessagesFromIntent(intent).joinToString("") { it.messageBody.orEmpty() }.take(16_384) }.getOrNull() ?: return
        if (text.isBlank()) return
        if (active.incrementAndGet() > 4) { active.decrementAndGet(); return }
        val pending = goAsync(); val finished = AtomicBoolean(false); val handler = Handler(Looper.getMainLooper())
        val finish = Runnable { if (finished.compareAndSet(false, true)) pending.finish() }
        handler.postDelayed(finish, 8500)
        scope.launch {
            try {
                val completed = withTimeoutOrNull(8000) { UrlIntake.process(context.applicationContext, text, ScanSource.SMS); true } ?: false
                if (!completed) AlertNotifier.notifyFailure(context)
            } catch (e: CancellationException) { throw e }
            catch (_: Exception) { AlertNotifier.notifyFailure(context) }
            finally { active.decrementAndGet(); handler.removeCallbacks(finish); finish.run() }
        }
    }
    companion object { private val active = AtomicInteger(); private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO) }
}
