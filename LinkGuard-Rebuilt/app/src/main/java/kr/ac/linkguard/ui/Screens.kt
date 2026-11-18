package kr.ac.linkguard.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kr.ac.linkguard.core.*
import kr.ac.linkguard.data.AppSettings
import java.net.URI
import java.time.Instant
import java.time.ZoneId

@Composable
fun PageTitle(eyebrow: String, title: String, description: String) {
    Column(Modifier.padding(top = 9.dp, bottom = 21.dp)) {
        Text(eyebrow, color = Mint, fontSize = 10.sp, letterSpacing = 1.6.sp)
        Text(title, fontSize = 27.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(vertical = 7.dp))
        Text(description, color = Muted, fontSize = 13.sp, lineHeight = 21.sp)
    }
}

@Composable
fun InfoNote(text: String, modifier: Modifier = Modifier) {
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp), color = Color(0xFF192A37),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
        Row(Modifier.padding(14.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Icon(Icons.Outlined.Info, null, Modifier.size(18.dp), tint = Mint)
            Text(text, color = Color(0xFFA9C2CB), fontSize = 12.sp, lineHeight = 20.sp)
        }
    }
}

@Composable
private fun Section(text: String, action: String? = null, onAction: () -> Unit = {}) {
    Row(Modifier.fillMaxWidth().padding(top = 23.dp, bottom = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(text, fontSize = 16.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
        if (action != null) TextButton(onClick = onAction, contentPadding = PaddingValues(0.dp)) { Text(action, fontSize = 12.sp) }
    }
}

@Composable
fun HomeScreen(settings: AppSettings, history: List<ScanResult>, smsActive: Boolean, notificationActive: Boolean,
    onToggle: () -> Unit, onScan: () -> Unit, onHistory: () -> Unit, onSelect: (ScanResult) -> Unit) {
    val active = smsActive || notificationActive
    val today = Instant.now().atZone(ZoneId.systemDefault()).toLocalDate()
    val recent = history.filter { Instant.ofEpochMilli(it.timestamp).atZone(ZoneId.systemDefault()).toLocalDate() == today }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 22.dp).padding(bottom = 25.dp)) {
        PageTitle("YOUR LINK SAFETY COMPANION", "안심은, 클릭 전에", "문자와 알림, QR 속 링크를 먼저 확인하세요.")
        Surface(shape = RoundedCornerShape(25.dp), border = BorderStroke(1.dp, Color(0xFF356A69)), color = Color.Transparent) {
            Column(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(Color(0xFF173D47), Color(0xFF102739), Color(0xFF142035)))).padding(22.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("나의 링크 보호", color = Color(0xFFB3D1D1), fontSize = 12.sp)
                    Text(if (active) "감지 채널 연결됨" else "설정 확인", color = if (active) Mint else Muted, fontSize = 11.sp)
                }
                Box(Modifier.padding(vertical = 24.dp).size(112.dp).background(Color(0xFF204C52), CircleShape), contentAlignment = Alignment.Center) {
                    Icon(Icons.Outlined.VerifiedUser, null, Modifier.size(56.dp), tint = if (active) Mint else Muted)
                }
                Text(if (active) "링크를 살펴보고 있어요" else if (settings.protectionEnabled) "감지 권한을 확인해 주세요" else "링크 보호를 시작하세요", fontWeight = FontWeight.Bold, fontSize = 19.sp)
                Text("허용된 채널에서 발견한 URL을 검사합니다.", color = Color(0xFFAEC9CC), fontSize = 11.sp, modifier = Modifier.padding(top = 8.dp, bottom = 20.dp))
                Button(onToggle, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp), shape = RoundedCornerShape(14.dp)) {
                    Icon(if (settings.protectionEnabled) Icons.Outlined.Pause else Icons.Outlined.PlayArrow, null, Modifier.size(19.dp))
                    Spacer(Modifier.width(8.dp)); Text(if (settings.protectionEnabled) "보호 중지" else "보호 시작", fontWeight = FontWeight.Bold)
                }
            }
        }
        Section("오늘의 검사")
        Row(horizontalArrangement = Arrangement.spacedBy(11.dp)) {
            Stat("검사한 링크", recent.size, "보관 중인 오늘 기록", Icons.Outlined.Link, Modifier.weight(1f))
            Stat("주의·위험", recent.count { it.level != RiskLevel.LOW }, "추가 확인이 필요한 링크", Icons.Outlined.WarningAmber, Modifier.weight(1f))
        }
        Section("보호 채널")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Channel("SMS", smsActive, Icons.Outlined.Sms, Modifier.weight(1f))
            Channel("앱 알림", notificationActive, Icons.Outlined.Notifications, Modifier.weight(1f))
            Channel("URL·QR", true, Icons.Outlined.QrCodeScanner, Modifier.weight(1f), "직접 검사")
        }
        OutlinedButton(onScan, Modifier.fillMaxWidth().padding(top = 16.dp), shape = RoundedCornerShape(14.dp)) { Text("URL 직접 검사하기") }
        Section("최근 탐지 기록", "전체 보기", onHistory)
        if (history.isEmpty()) InfoNote("아직 기록이 없어요. URL을 입력하거나 QR 코드를 스캔해 보세요.")
        history.take(3).forEach { result -> HistoryRow(result) { onSelect(result) }; Spacer(Modifier.height(8.dp)) }
        Text(if (settings.remoteEnabled) "현재 분석 방식 · AI 서버" else "현재 분석 방식 · 로컬 규칙", color = Muted, fontSize = 11.sp, modifier = Modifier.padding(top = 16.dp))
    }
}

@Composable
private fun Stat(title: String, count: Int, detail: String, icon: ImageVector, modifier: Modifier) {
    Surface(modifier, shape = RoundedCornerShape(17.dp), color = Panel) {
        Column(Modifier.padding(15.dp)) {
            Row(Modifier.fillMaxWidth()) { Text(title, fontSize = 11.sp, color = Muted, modifier = Modifier.weight(1f)); Icon(icon, null, Modifier.size(18.dp), tint = Mint) }
            Text("$count", fontSize = 31.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 7.dp))
            Text(detail, fontSize = 10.sp, color = Muted)
        }
    }
}

@Composable
private fun Channel(title: String, active: Boolean, icon: ImageVector, modifier: Modifier, activeText: String = "감지 중") {
    Surface(modifier, color = Panel, shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.padding(horizontal = 4.dp, vertical = 16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, null, Modifier.size(24.dp), tint = if (active) Mint else Muted)
            Text(title, fontWeight = FontWeight.Bold, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp))
            Text(if (active) activeText else "꺼짐", color = if (active) Mint else Muted, fontSize = 10.sp, modifier = Modifier.padding(top = 5.dp))
        }
    }
}

@Composable
fun UrlScreen(input: String, onInput: (String) -> Unit, remote: Boolean, busy: Boolean, error: String?, onAnalyze: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(horizontal = 22.dp).padding(bottom = 24.dp)) {
        PageTitle("CHECK BEFORE YOU CLICK", "URL 직접 검사", "사이트를 열기 전에 주소를 붙여넣어 주세요.")
        Surface(shape = RoundedCornerShape(21.dp), color = Panel) {
            Column(Modifier.padding(18.dp)) {
                Text("검사할 링크", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                OutlinedTextField(input, { if (it.length <= 4096) onInput(it) }, modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    placeholder = { Text("https://example.com") }, minLines = 2, maxLines = 5, shape = RoundedCornerShape(13.dp),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Go),
                    keyboardActions = KeyboardActions(onGo = { if (!busy) onAnalyze() }), isError = error != null)
                if (error != null) Text(error, fontSize = 12.sp, lineHeight = 20.sp, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 10.dp))
                Text(if (remote) "입력한 URL만 설정된 AI 서버로 전송합니다." else "기기 안에서 URL의 구조적 위험 신호를 확인합니다.", color = Muted, fontSize = 11.sp, lineHeight = 19.sp, modifier = Modifier.padding(top = 12.dp))
                Button(onAnalyze, enabled = !busy && input.isNotBlank(), modifier = Modifier.fillMaxWidth().padding(top = 18.dp).heightIn(min = 50.dp), shape = RoundedCornerShape(14.dp)) {
                    if (busy) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp) else Icon(Icons.Outlined.Search, null, Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp)); Text(if (busy) "분석 중…" else "URL 분석하기")
                }
            }
        }
        Section("테스트용 URL")
        listOf("일반적인 HTTPS 형태" to "https://www.example.com", "배송·인증 문자열 형태" to "http://delivery-verify.example/login", "IP 주소 형태" to "http://192.0.2.10/verify").forEach { (label, value) ->
            OutlinedButton({ onInput(value) }, Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) {
                Column(Modifier.fillMaxWidth()) { Text(label, fontSize = 12.sp); Text(value, fontSize = 10.sp, color = Muted) }
            }
        }
        InfoNote(if (remote) "서버 점수는 상대적인 위험 신호입니다. 연결 오류는 검사 실패로 표시합니다. 주소를 자동으로 열지 않습니다." else "로컬 규칙 점수는 AI 예측이나 실제 안전성 판정이 아닙니다. 낮은 점수라도 발신자와 주소를 확인하세요.", Modifier.padding(top = 16.dp))
    }
}

@Composable
fun SettingsScreen(settings: AppSettings, smsGranted: Boolean, notificationGranted: Boolean, alertsGranted: Boolean,
    onChange: ((AppSettings) -> AppSettings) -> Unit, onSms: (Boolean) -> Unit, onNotifications: (Boolean) -> Unit,
    onSmsPermission: () -> Unit, onNotificationPermission: () -> Unit, onWarningPermission: () -> Unit, onSaved: () -> Unit) {
    var server by rememberSaveable(settings.serverUrl) { mutableStateOf(settings.serverUrl) }
    var error by remember { mutableStateOf<String?>(null) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(horizontal = 22.dp).padding(bottom = 28.dp)) {
        PageTitle("PROTECTION SETTINGS", "보호 설정", "감지할 채널과 분석 방식을 선택하세요.")
        ToggleRow("SMS 링크 감지", if (smsGranted) "SMS 수신 권한 허용됨" else "SMS 수신 권한이 필요합니다", settings.smsEnabled, onSms)
        ToggleRow("앱 알림 URL 감지", if (notificationGranted) "알림 접근 권한 허용됨" else "기기 설정에서 알림 접근을 허용하세요", settings.notificationEnabled, onNotifications)
        ToggleRow("위험 경고 알림", if (alertsGranted) "주의·위험 결과를 시스템 알림으로 표시" else "알림 권한과 경고 채널 설정을 확인하세요", settings.warningEnabled) { enabled -> onChange { it.copy(warningEnabled = enabled) } }
        Section("권한 관리")
        PermissionRow("SMS 수신 권한", smsGranted, onSmsPermission)
        PermissionRow("다른 앱의 알림 접근", notificationGranted, onNotificationPermission)
        PermissionRow("시스템 경고 알림", alertsGranted, onWarningPermission)
        InfoNote("자동 감지는 홈에서 보호를 시작한 뒤 작동합니다. 메신저·메일은 알림에 표시된 내용에서만 URL을 추출합니다.", Modifier.padding(top = 12.dp))
        Section("분석 엔진")
        ToggleRow("AI 서버 사용", "꺼짐: 기기 내 로컬 규칙 분석", settings.remoteEnabled) { enabled ->
            if (enabled && settings.serverUrl.isBlank()) error = "먼저 HTTPS 서버 주소를 저장해 주세요."
            else onChange { it.copy(remoteEnabled = enabled) }
        }
        OutlinedTextField(server, { server = it.take(2048); error = null }, modifier = Modifier.fillMaxWidth().padding(top = 14.dp),
            label = { Text("AI 서버 기본 주소") }, placeholder = { Text("https://api.your-domain.com") }, singleLine = true,
            shape = RoundedCornerShape(13.dp), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri), isError = error != null)
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, fontSize = 12.sp, modifier = Modifier.padding(top = 8.dp)) }
        OutlinedButton({
            val value = server.trim().trimEnd('/')
            val valid = runCatching { val parsed = URI(UrlTools.normalize(value)); parsed.scheme == "https" && !parsed.host.isNullOrBlank() && parsed.rawUserInfo == null && parsed.rawQuery == null && parsed.rawFragment == null }.getOrDefault(false)
            if (value.isNotEmpty() && !valid) error = "인증정보·쿼리가 없는 HTTPS 주소를 입력하세요."
            else {
                runCatching { onChange { it.copy(serverUrl = value, remoteEnabled = it.remoteEnabled && value.isNotEmpty()) } }
                    .onSuccess { server = value; error = null; onSaved() }
                    .onFailure { error = it.message ?: "서버 주소를 확인해 주세요." }
            }
        }, Modifier.fillMaxWidth().padding(top = 10.dp), shape = RoundedCornerShape(13.dp)) { Text("서버 주소 저장") }
        InfoNote("AI 서버를 켜면 추출한 URL만 해당 서버로 전송합니다. 학습된 모델은 별도로 준비해야 하며 연결 오류를 정상 판정으로 바꾸지 않습니다.", Modifier.padding(top = 12.dp))
        Section("데이터 보관")
        InfoNote("검사 결과는 기기에 최대 200개 보관합니다. 문자·알림 본문은 저장하지 않습니다. 기록 탭에서 전체 삭제할 수 있습니다. 앱 데이터는 자동 백업과 기기 이전에서 제외합니다.")
        Text("LINKGUARD · REBUILT v0.2.0", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(top = 24.dp).align(Alignment.CenterHorizontally))
    }
}

@Composable
private fun ToggleRow(title: String, description: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Surface(Modifier.fillMaxWidth().padding(bottom = 8.dp), color = Panel, shape = RoundedCornerShape(14.dp)) {
        Row(Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f).padding(end = 10.dp)) {
                Text(title, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text(description, fontSize = 11.sp, color = Muted, lineHeight = 17.sp, modifier = Modifier.padding(top = 4.dp))
            }
            Switch(checked, onChange)
        }
    }
}

@Composable
private fun PermissionRow(title: String, granted: Boolean, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { Text(title, fontSize = 13.sp); Text(if (granted) "허용됨" else "권한 확인 필요", color = if (granted) Mint else Color(0xFFFFCF79), fontSize = 11.sp) }
        TextButton(onClick) { Text(if (granted) "관리" else "허용", fontSize = 12.sp) }
    }
}
