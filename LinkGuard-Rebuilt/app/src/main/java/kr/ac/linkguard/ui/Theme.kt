package kr.ac.linkguard.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Mint = Color(0xFF65ECCD)
val Muted = Color(0xFF91A4B8)
val Panel = Color(0xFF132438)

@Composable
fun LinkGuardTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = darkColorScheme(primary = Mint, onPrimary = Color(0xFF09382F),
        primaryContainer = Color(0xFF1A423C), background = Color(0xFF0B1523),
        surface = Color(0xFF101E2D), surfaceVariant = Panel, onSurface = Color(0xFFF5FBFF),
        onBackground = Color(0xFFF5FBFF), onSurfaceVariant = Muted, outline = Color(0xFF2B4158),
        error = Color(0xFFFF7988)), content = content)
}
