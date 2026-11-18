package kr.ac.linkguard.background
import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import kr.ac.linkguard.LinkGuardApplication
import kr.ac.linkguard.MainActivity
import kr.ac.linkguard.core.*
import java.net.URI
object AlertNotifier {
    const val CHANNEL_ID = "linkguard_warnings"
    const val RESULT_ID_EXTRA = "result_id"
    private fun manager(context: Context): NotificationManager = context.getSystemService(NotificationManager::class.java).apply {
        createNotificationChannel(NotificationChannel(CHANNEL_ID, "링크 위험 경고", NotificationManager.IMPORTANCE_HIGH).apply { description = "수신 링크의 주의·위험 결과를 안내합니다."; lockscreenVisibility = Notification.VISIBILITY_PRIVATE })
    }
    @SuppressLint("MissingPermission") // PermissionHelper checks runtime, app and channel permissions.
    fun notifyResult(context: Context, result: ScanResult) {
        val config = (context.applicationContext as LinkGuardApplication).repository.settings.value
        if (!config.protectionEnabled || !config.warningEnabled || result.level == RiskLevel.LOW || !PermissionHelper.alertsGranted(context)) return
        val host = runCatching { URI(result.normalizedUrl).host }.getOrNull()?.filter { !it.isISOControl() }?.take(100) ?: "수신한 링크"
        val mode = if (result.mode == AnalysisMode.LOCAL_RULES) "로컬 규칙 분석" else "AI 서버 분석"
        val intent = Intent(context, MainActivity::class.java).putExtra(RESULT_ID_EXTRA, result.id).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val pending = PendingIntent.getActivity(context, result.id.hashCode(), intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(context, CHANNEL_ID).setSmallIcon(android.R.drawable.ic_dialog_alert).setContentTitle("링크를 열기 전에 확인해 주세요").setContentText("$host · $mode").setContentIntent(pending).setVisibility(Notification.VISIBILITY_PRIVATE).setAutoCancel(true).build()
        runCatching { manager(context).notify(result.id.hashCode(), notification) }
    }
    @SuppressLint("MissingPermission")
    fun notifyFailure(context: Context) {
        val config = (context.applicationContext as LinkGuardApplication).repository.settings.value
        if (!config.protectionEnabled || !config.warningEnabled || !PermissionHelper.alertsGranted(context)) return
        val pending = PendingIntent.getActivity(context, 910, Intent(context, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        runCatching { manager(context).notify(910, Notification.Builder(context, CHANNEL_ID).setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("자동 검사를 완료하지 못했어요").setContentText("연결과 서버 설정을 확인하고 직접 검사해 주세요.").setContentIntent(pending).setAutoCancel(true).setOnlyAlertOnce(true).setVisibility(Notification.VISIBILITY_PRIVATE).build()) }
    }
}
