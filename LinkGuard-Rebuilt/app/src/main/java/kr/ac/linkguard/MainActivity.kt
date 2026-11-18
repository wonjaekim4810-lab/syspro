package kr.ac.linkguard

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kr.ac.linkguard.background.PermissionHelper
import kr.ac.linkguard.core.*
import kr.ac.linkguard.data.LinkGuardRepository
import kr.ac.linkguard.ui.*

class MainActivity : ComponentActivity() {
    private val sharedText = mutableStateOf<String?>(null)
    private val resultId = mutableStateOf<String?>(null)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        receiveIntent(intent)
        setContent {
            LinkGuardTheme {
                LinkGuardApp((application as LinkGuardApplication).repository, sharedText.value,
                    resultId.value, { sharedText.value = null }, { resultId.value = null })
            }
        }
    }
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        receiveIntent(intent)
    }
    private fun receiveIntent(intent: Intent) {
        resultId.value = intent.getStringExtra("result_id")
        if (intent.action == Intent.ACTION_SEND && intent.type == "text/plain")
            sharedText.value = intent.getStringExtra(Intent.EXTRA_TEXT)?.take(16_384)
    }
}

@Composable
private fun LinkGuardApp(repository: LinkGuardRepository, incoming: String?, resultId: String?,
    onIncomingHandled: () -> Unit, onResultHandled: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val settings by repository.settings.collectAsStateWithLifecycle()
    val history by repository.history.collectAsStateWithLifecycle()
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var input by rememberSaveable { mutableStateOf("") }
    var source by remember { mutableStateOf(ScanSource.MANUAL) }
    var selected by remember { mutableStateOf<ScanResult?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var revision by remember { mutableIntStateOf(0) }
    val lifecycle = LocalLifecycleOwner.current
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_RESUME) revision++ }
        lifecycle.lifecycle.addObserver(observer)
        onDispose { lifecycle.lifecycle.removeObserver(observer) }
    }
    val smsGranted = remember(revision) { PermissionHelper.smsGranted(context) }
    val notificationGranted = remember(revision) { PermissionHelper.notificationAccessGranted(context) }
    val alertsGranted = remember(revision) { PermissionHelper.alertsGranted(context) }
    val smsActive = settings.protectionEnabled && settings.smsEnabled && smsGranted
    val notificationActive = settings.protectionEnabled && settings.notificationEnabled && notificationGranted
    val active = smsActive || notificationActive
    val scope = rememberCoroutineScope()
    val snackbars = remember { SnackbarHostState() }
    val smsPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        repository.updateSettings { it.copy(smsEnabled = granted) }
        revision++
        if (!granted) scope.launch { snackbars.showSnackbar("SMS 권한이 없어 자동 감지가 꺼져 있어요. 기기 설정에서 허용할 수 있어요.") }
    }
    val warningPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        revision++
        if (!granted) scope.launch { snackbars.showSnackbar("알림 권한이 없어 시스템 경고가 표시되지 않아요.") }
    }
    fun analyze(value: String, scanSource: ScanSource) {
        if (busy) return
        busy = true
        error = null
        scope.launch {
            try { selected = repository.analyze(value, scanSource) }
            catch (cancelled: CancellationException) { throw cancelled }
            catch (failure: Exception) { error = failure.message ?: "검사하지 못했어요. 다시 시도해 주세요."; tab = 1 }
            finally { busy = false }
        }
    }
    LaunchedEffect(incoming) {
        if (incoming != null) {
            input = UrlTools.extract(incoming).firstOrNull() ?: incoming
            source = ScanSource.SHARE
            error = null
            tab = 1
            onIncomingHandled()
        }
    }
    LaunchedEffect(resultId) {
        if (resultId != null) {
            selected = repository.findResult(resultId)
            if (selected == null) snackbars.showSnackbar("이 기록이 삭제되었거나 보관 기간을 벗어났어요.")
            onResultHandled()
        }
    }
    val labels = listOf("홈", "URL 검사", "QR 검사", "기록", "설정")
    val icons = listOf(Icons.Outlined.Home, Icons.Outlined.Search, Icons.Outlined.QrCodeScanner,
        Icons.Outlined.History, Icons.Outlined.Settings)
    Scaffold(
        snackbarHost = { SnackbarHost(snackbars) },
        topBar = {
            Column(Modifier.windowInsetsPadding(WindowInsets.statusBars)) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 22.dp, vertical = 15.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.VerifiedUser, null, tint = Mint, modifier = Modifier.size(33.dp))
                    Column(Modifier.weight(1f).padding(start = 10.dp)) {
                        Text("LinkGuard", style = MaterialTheme.typography.titleLarge)
                        Text("클릭 전, 링크를 확인하세요", color = Muted, fontSize = 10.sp)
                    }
                    Text(if (active) "● 보호 중" else if (settings.protectionEnabled) "권한 확인" else "보호 꺼짐",
                        color = if (active) Mint else Muted, fontSize = 11.sp)
                }
                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            }
        },
        bottomBar = {
            NavigationBar {
                labels.forEachIndexed { index, label ->
                    NavigationBarItem(selected = tab == index, onClick = { tab = index },
                        icon = { Icon(icons[index], null, Modifier.size(22.dp)) },
                        label = { Text(label, fontSize = 10.sp, maxLines = 1) },
                        colors = NavigationBarItemDefaults.colors(selectedIconColor = Mint, selectedTextColor = Mint))
                }
            }
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (tab) {
                0 -> HomeScreen(settings, history, smsActive, notificationActive, onToggle = {
                    val enabling = !settings.protectionEnabled
                    repository.updateSettings { it.copy(protectionEnabled = enabling) }
                    if (enabling && !(settings.smsEnabled && smsGranted || settings.notificationEnabled && notificationGranted)) {
                        tab = 4
                        scope.launch { snackbars.showSnackbar("감지할 채널과 필요한 권한을 설정해 주세요.") }
                    }
                }, onScan = { tab = 1 }, onHistory = { tab = 3 }, onSelect = { selected = it })
                1 -> UrlScreen(input, { input = it; source = ScanSource.MANUAL; error = null },
                    settings.remoteEnabled, busy, error) { analyze(input, source) }
                2 -> QrScreen { value -> input = value; source = ScanSource.QR; tab = 1; analyze(value, ScanSource.QR) }
                3 -> HistoryScreen(history, { selected = it }, { repository.clearHistory(); selected = null })
                4 -> SettingsScreen(settings, smsGranted, notificationGranted, alertsGranted, repository::updateSettings,
                    onSms = { enabled ->
                        if (!enabled || smsGranted) repository.updateSettings { it.copy(smsEnabled = enabled) }
                        else smsPermission.launch(Manifest.permission.RECEIVE_SMS)
                    },
                    onNotifications = { enabled ->
                        repository.updateSettings { it.copy(notificationEnabled = enabled) }
                        if (enabled && !notificationGranted) PermissionHelper.openNotificationAccess(context)
                    },
                    onSmsPermission = { context.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                        Uri.parse("package:${context.packageName}"))) },
                    onNotificationPermission = { PermissionHelper.openNotificationAccess(context) },
                    onWarningPermission = {
                        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
                            warningPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                        else PermissionHelper.openAlertSettings(context)
                    }, onSaved = { scope.launch { snackbars.showSnackbar("서버 주소를 저장했어요.") } })
            }
        }
    }
    selected?.let { ResultSheet(it) { selected = null } }
}
