package kr.ac.linkguard.core

import java.net.IDN
import java.net.InetAddress
import java.net.URI
import java.util.Locale

/** URL string parsing only; does not retrieve websites or resolve DNS names. */
object UrlTools {
    const val MAX_LENGTH = 4096
    private val scheme = Regex("^[A-Za-z][A-Za-z0-9+.-]*:")
    private val explicit = Regex("^https?://", RegexOption.IGNORE_CASE)
    private val barePort = Regex("^[^/:?#]+\\.[^/:?#]+:[0-9]+(?:[/?#]|$)")
    private val inText = Regex("https?://[^\\s<>\\\"'\\u0000-\\u001F]+", RegexOption.IGNORE_CASE)
    fun normalize(input: String): String {
        require(input.length <= MAX_LENGTH) { "URL은 4,096자 이하로 입력해 주세요." }
        require(input.none { it.code < 32 || it.code == 127 }) { "제어 문자를 포함한 URL은 지원하지 않아요." }
        var index = 0
        while (index < input.length) {
            val char = input[index]
            if (Character.isHighSurrogate(char)) {
                require(index + 1 < input.length && Character.isLowSurrogate(input[index + 1])) { "URL의 유니코드 문자를 확인해 주세요." }
                index += 2
            } else {
                require(!Character.isLowSurrogate(char)) { "URL의 유니코드 문자를 확인해 주세요." }
                index++
            }
        }
        val text = input.trim()
        require(text.isNotBlank() && text.none { it.isWhitespace() || it == '\\' }) { "올바른 URL을 입력해 주세요." }
        require(!text.startsWith("//") && (explicit.containsMatchIn(text) || !scheme.containsMatchIn(text) || barePort.containsMatchIn(text) || text.startsWith("["))) { "http 또는 https URL만 지원해요." }
        val uri = try { URI(if (explicit.containsMatchIn(text)) text else "https://$text") } catch (_: Exception) { throw IllegalArgumentException("URL 형식을 확인해 주세요.") }
        require(uri.scheme.equals("http", true) || uri.scheme.equals("https", true)) { "http 또는 https URL만 지원해요." }
        val authority = uri.rawAuthority ?: throw IllegalArgumentException("URL 호스트를 확인해 주세요.")
        require(!authority.contains('@') && uri.rawUserInfo == null) { "사용자 정보가 포함된 URL은 지원하지 않아요." }
        val (rawHost, port) = if (authority.startsWith("[")) {
            val end = authority.indexOf(']')
            require(end > 1) { "IPv6 형식을 확인해 주세요." }
            val h = authority.substring(1, end)
            require(h.matches(Regex("[0-9a-fA-F:.]+")) && h.contains(':') && runCatching { InetAddress.getByName(h); true }.getOrDefault(false)) { "IPv6 형식을 확인해 주세요." }
            "[$h]" to authority.substring(end + 1)
        } else {
            require(authority.count { it == ':' } <= 1) { "IPv6 주소는 대괄호로 감싸 주세요." }
            val colon = authority.lastIndexOf(':')
            if (colon < 0) authority to "" else authority.substring(0, colon) to authority.substring(colon)
        }
        require(port.isEmpty() || port.matches(Regex(":[0-9]{1,5}")) && port.drop(1).toInt() in 1..65535) { "포트는 1~65535 범위여야 해요." }
        val host = if (rawHost.startsWith('[')) rawHost.lowercase(Locale.ROOT) else {
            val ascii = try { IDN.toASCII(rawHost, IDN.USE_STD3_ASCII_RULES).lowercase(Locale.ROOT).removeSuffix(".") } catch (_: Exception) { throw IllegalArgumentException("도메인 형식을 확인해 주세요.") }
            require(ascii.length <= 253 && ascii.contains('.') && ascii.split('.').all { it.isNotEmpty() && it.length <= 63 }) { "올바른 도메인을 입력해 주세요." }
            if (ascii.matches(Regex("[0-9.]+"))) require(isIpv4(ascii)) { "IPv4 형식을 확인해 주세요." }
            ascii
        }
        return buildString {
            append(uri.scheme.lowercase(Locale.ROOT)); append("://"); append(host); append(port); append(uri.rawPath.orEmpty())
            uri.rawQuery?.let { append('?'); append(it) }; uri.rawFragment?.let { append('#'); append(it) }
        }.also { require(it.length <= MAX_LENGTH) { "정규화한 URL이 너무 길어요." } }
    }
    fun extract(text: String): List<String> = inText.findAll(text).mapNotNull { match ->
        var candidate = match.value.trimEnd('.', ',', ';', '!', '?', '。', '，', '」', '』', '》', '〉')
        for ((open, close) in listOf('(' to ')', '[' to ']', '{' to '}')) {
            while (candidate.endsWith(close) && candidate.count { it == close } > candidate.count { it == open }) candidate = candidate.dropLast(1)
        }
        runCatching { normalize(candidate) }.getOrNull()
    }.distinct().take(20).toList()
    internal fun isIpv4(host: String): Boolean = host.split('.').let { parts -> parts.size == 4 && parts.all { it.matches(Regex("[0-9]{1,3}")) && (it.length == 1 || !it.startsWith('0')) && it.toInt() in 0..255 } }
}
