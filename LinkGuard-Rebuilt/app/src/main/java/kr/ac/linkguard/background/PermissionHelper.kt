package kr.ac.linkguard.background
import android.Manifest
import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
object PermissionHelper {
    fun smsGranted(context: Context) = context.checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED
    fun notificationAccessGranted(context: Context): Boolean {
        val expected = ComponentName(context, LinkNotificationListener::class.java)
        return Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners")?.split(':')?.mapNotNull(ComponentName::unflattenFromString)?.any { it == expected } == true
    }
    fun alertsGranted(context: Context): Boolean {
        val manager = context.getSystemService(NotificationManager::class.java)
        return (Build.VERSION.SDK_INT < 33 || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) && manager.areNotificationsEnabled() && manager.getNotificationChannel(AlertNotifier.CHANNEL_ID)?.importance != NotificationManager.IMPORTANCE_NONE
    }
    fun openNotificationAccess(context: Context) { context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
    fun openAlertSettings(context: Context) { context.startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
}
