package kr.ac.linkguard.ui

import android.content.ActivityNotFoundException
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CameraAlt
import androidx.compose.material.icons.outlined.QrCodeScanner
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import kr.ac.linkguard.core.UrlTools

@Composable
fun QrScreen(onUrlScanned: (String) -> Unit) {
    var message by rememberSaveable { mutableStateOf<String?>(null) }
    val scanner = rememberLauncherForActivityResult(ScanContract()) { result ->
        val content = result.contents
        if (content.isNullOrBlank()) message = "스캔을 취소했거나 카메라를 사용할 수 없어요. 카메라 권한을 확인해 주세요."
        else {
            val normalized = runCatching { UrlTools.normalize(content) }.getOrNull()
            if (normalized == null) message = "웹 주소가 담긴 QR 코드가 아니에요. http 또는 https 주소를 확인해 주세요."
            else { message = null; onUrlScanned(normalized) }
        }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 22.dp).padding(bottom = 24.dp)) {
        PageTitle("QR LINK CHECK", "QR 코드 검사", "QR에 담긴 주소를 확인하고, 접속 전에 위험 신호를 살펴보세요.")
        Surface(Modifier.fillMaxWidth().height(270.dp), color = Panel, shape = RoundedCornerShape(24.dp), border = BorderStroke(1.dp, Mint.copy(alpha = .3f))) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                Icon(Icons.Outlined.QrCodeScanner, null, Modifier.size(124.dp), tint = Mint)
                Text("카메라로 QR 코드를 스캔하세요", color = Muted, modifier = Modifier.padding(top = 22.dp))
            }
        }
        Button(onClick = {
            message = null
            try {
                scanner.launch(ScanOptions().setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                    .setPrompt("웹 주소가 담긴 QR 코드를 화면에 맞춰주세요")
                    .setBeepEnabled(false).setBarcodeImageEnabled(false).setOrientationLocked(false))
            } catch (_: ActivityNotFoundException) { message = "스캐너를 열 수 없어요. URL을 직접 입력해 주세요." }
            catch (_: SecurityException) { message = "기기 설정에서 카메라 권한을 허용해 주세요." }
        }, modifier = Modifier.fillMaxWidth().padding(top = 18.dp).heightIn(min = 52.dp), shape = RoundedCornerShape(14.dp)) {
            Icon(Icons.Outlined.CameraAlt, null, Modifier.size(20.dp)); Spacer(Modifier.width(9.dp)); Text("카메라로 QR 스캔")
        }
        message?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(vertical = 14.dp)) }
        InfoNote("QR 이미지는 기기에서 해독하며 저장하지 않아요. 웹 주소만 공통 분석기로 전달합니다. AI 서버를 켠 경우에는 주소만 설정한 서버로 전송합니다. 링크를 자동으로 열지 않습니다.", Modifier.padding(top = 20.dp))
    }
}
