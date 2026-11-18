package kr.ac.linkguard.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ChevronRight
import androidx.compose.material.icons.outlined.WarningAmber
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kr.ac.linkguard.core.*
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

fun riskColor(level: RiskLevel): Color = when (level) {
    RiskLevel.LOW -> Mint
    RiskLevel.CAUTION -> Color(0xFFFFCF79)
    RiskLevel.HIGH -> Color(0xFFFF7988)
}
fun riskLabel(level: RiskLevel): String = when (level) {
    RiskLevel.LOW -> "낮은 위험"
    RiskLevel.CAUTION -> "주의"
    RiskLevel.HIGH -> "위험"
}
private fun modeLabel(mode: AnalysisMode) = if (mode == AnalysisMode.LOCAL_RULES) "로컬 규칙 분석" else "AI 서버 분석"
private fun timeLabel(timestamp: Long) = SimpleDateFormat("M월 d일 HH:mm", Locale.KOREA).format(Date(timestamp))

@Composable
fun HistoryScreen(history: List<ScanResult>, onSelect: (ScanResult) -> Unit, onClear: () -> Unit) {
    var filter by rememberSaveable { mutableIntStateOf(0) }
    var confirm by remember { mutableStateOf(false) }
    val selected = history.filter { filter == 0 || filter == 1 && it.level != RiskLevel.LOW || filter == 2 && it.level == RiskLevel.LOW }
    Column(Modifier.fillMaxSize().padding(horizontal = 22.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) { PageTitle("SCAN ACTIVITY", "탐지 기록", "검사한 주소와 판단 근거를 확인하세요.") }
            TextButton(onClick = { confirm = true }, enabled = history.isNotEmpty()) { Text("삭제") }
        }
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("전체 ${history.size}", "주의·위험 ${history.count { it.level != RiskLevel.LOW }}", "낮은 위험 ${history.count { it.level == RiskLevel.LOW }}").forEachIndexed { index, label ->
                FilterChip(selected = filter == index, onClick = { filter = index }, label = { Text(label) })
            }
        }
        if (selected.isEmpty()) Box(Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.Center) { Text("표시할 기록이 없어요.", color = Muted) }
        else LazyColumn(Modifier.weight(1f).padding(top = 10.dp), verticalArrangement = Arrangement.spacedBy(9.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
            items(selected, key = { it.id }) { result -> HistoryRow(result) { onSelect(result) } }
            item { Text("기기에 최대 200개 보관합니다.", color = Muted, fontSize = 11.sp, modifier = Modifier.padding(top = 10.dp)) }
        }
    }
    if (confirm) AlertDialog(onDismissRequest = { confirm = false }, title = { Text("기록을 모두 삭제할까요?") },
        text = { Text("기기에 저장된 ${history.size}개 검사 기록을 삭제합니다.") },
        confirmButton = { TextButton(onClick = { onClear(); confirm = false }) { Text("모두 삭제") } },
        dismissButton = { TextButton(onClick = { confirm = false }) { Text("취소") } })
}

@Composable
fun HistoryRow(result: ScanResult, onClick: () -> Unit) {
    val color = riskColor(result.level)
    Surface(onClick = onClick, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(15.dp), color = Panel) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(11.dp)) {
            Icon(Icons.Outlined.WarningAmber, null, Modifier.size(23.dp), tint = color)
            Column(Modifier.weight(1f)) {
                Text(result.normalizedUrl, maxLines = 1, overflow = TextOverflow.Ellipsis, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                Text("${result.source.label} · ${timeLabel(result.timestamp)}", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(top = 5.dp))
                Text(modeLabel(result.mode), color = Muted, fontSize = 10.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(riskLabel(result.level), color = color, fontSize = 11.sp)
                Text("${result.score}점", color = Muted, fontSize = 10.sp)
            }
            Icon(Icons.Outlined.ChevronRight, null, Modifier.size(15.dp), tint = Muted)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultSheet(result: ScanResult, onDismiss: () -> Unit) {
    val color = riskColor(result.level)
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().heightIn(max = 740.dp).verticalScroll(rememberScrollState()).navigationBarsPadding().padding(horizontal = 24.dp).padding(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(17.dp)) {
            Text("${modeLabel(result.mode)} · ${riskLabel(result.level)}", color = color, fontWeight = FontWeight.Bold)
            Text(when (result.level) { RiskLevel.LOW -> "뚜렷한 위험 신호가 적어요"; RiskLevel.CAUTION -> "추가 확인이 필요해요"; RiskLevel.HIGH -> "위험 신호가 발견됐어요" }, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Surface(color = Panel, shape = RoundedCornerShape(13.dp), modifier = Modifier.fillMaxWidth()) {
                SelectionContainer { Text(result.normalizedUrl, fontSize = 13.sp, modifier = Modifier.padding(15.dp)) }
            }
            Text("${result.source.label} · ${timeLabel(result.timestamp)}", color = Muted, fontSize = 11.sp)
            Text("상대 위험 점수", color = Muted, fontSize = 12.sp)
            Text("${result.score} / 100", color = color, fontSize = 38.sp, fontWeight = FontWeight.Bold)
            LinearProgressIndicator(progress = { result.score.coerceIn(0, 100) / 100f }, color = color, modifier = Modifier.fillMaxWidth())
            Text("표시 근거", fontWeight = FontWeight.Bold)
            result.reasons.forEach { Text("• $it", fontSize = 13.sp, lineHeight = 21.sp) }
            result.modelVersion?.let { Text("모델 버전 · $it", color = Muted, fontSize = 11.sp) }
            InfoNote(if (result.mode == AnalysisMode.LOCAL_RULES) "학습 모델이 아닌 URL 구조 규칙의 결과입니다. 점수는 피싱 확률이나 안전 보증이 아닙니다. 링크를 자동으로 열지 않습니다." else "모델 점수는 보정된 확률이나 안전 보증이 아닙니다. 표시 근거는 URL에서 관찰한 특징이며 모델의 실제 기여도 설명이 아닙니다.")
            Button(onDismiss, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp)) { Text("확인") }
        }
    }
}
