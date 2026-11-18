package kr.ac.linkguard
import android.app.Application
import kr.ac.linkguard.data.LinkGuardRepository
class LinkGuardApplication : Application() { val repository: LinkGuardRepository by lazy { LinkGuardRepository(this) } }
