# LinkGuard 재구성 소스 전체

원본 복구본이 아닌 대화 기반 재구성본입니다. 스키마/동작/검증 범위는 README.md를 확인하세요.

## 파일 목록

```text
.gitignore
API_CONTRACT.md
README.md
RECONSTRUCTION.json
app/build.gradle.kts
app/src/main/AndroidManifest.xml
app/src/main/java/kr/ac/linkguard/LinkGuardApplication.kt
app/src/main/java/kr/ac/linkguard/MainActivity.kt
app/src/main/java/kr/ac/linkguard/background/AlertNotifier.kt
app/src/main/java/kr/ac/linkguard/background/LinkNotificationListener.kt
app/src/main/java/kr/ac/linkguard/background/PermissionHelper.kt
app/src/main/java/kr/ac/linkguard/background/SmsReceiver.kt
app/src/main/java/kr/ac/linkguard/background/UrlIntake.kt
app/src/main/java/kr/ac/linkguard/core/Models.kt
app/src/main/java/kr/ac/linkguard/core/RuleAnalyzer.kt
app/src/main/java/kr/ac/linkguard/core/UrlTools.kt
app/src/main/java/kr/ac/linkguard/data/LinkGuardRepository.kt
app/src/main/java/kr/ac/linkguard/data/PredictionParser.kt
app/src/main/java/kr/ac/linkguard/ui/HistoryAndResult.kt
app/src/main/java/kr/ac/linkguard/ui/QrScreen.kt
app/src/main/java/kr/ac/linkguard/ui/Screens.kt
app/src/main/java/kr/ac/linkguard/ui/Theme.kt
app/src/main/res/drawable/ic_linkguard.xml
app/src/main/res/values/styles.xml
app/src/main/res/xml/data_extraction_rules.xml
app/src/test/java/kr/ac/linkguard/core/RuleAnalyzerTest.kt
app/src/test/java/kr/ac/linkguard/core/UrlToolsTest.kt
app/src/test/java/kr/ac/linkguard/data/PredictionParserTest.kt
build.gradle.kts
docs/IMPLEMENTATION.md
gradle/wrapper/gradle-wrapper.jar
gradle/wrapper/gradle-wrapper.properties
gradle.properties
gradlew
gradlew.bat
server/README.md
server/data/FORMAT.md
server/detector.py
server/docs/FEATURES.md
server/linkguard/__init__.py
server/linkguard/features.py
server/linkguard/model.py
server/linkguard/nlp.py
server/linkguard/resources/brands.json
server/linkguard/resources/corpus.txt
server/linkguard/resources/dictionary.txt
server/linkguard/resources/keywords.txt
server/linkguard/resources/known_tlds.txt
server/linkguard/training.py
server/linkguard/urltools.py
server/pyproject.toml
server/requirements-dev.txt
server/requirements-lock.txt
server/requirements.txt
server/server.py
server/tests/test_api.py
server/tests/test_features.py
server/tests/test_training.py
server/tests/test_urltools.py
server/train.py
settings.gradle.kts
```

## API_CONTRACT.md

```text
# Kotlin–Python API 계약

이 규격은 대화 내용을 바탕으로 재구성한 프로젝트의 계약입니다. Python 코드는 [server/](server/README.md)에 있습니다. 학습된 모델은 포함하지 않습니다.

```http
POST /predict
Content-Type: application/json
Accept: application/json

{"url":"https://www.example.com"}
```

```json
{
  "url": "https://www.example.com",
  "status": "caution",
  "score": 57,
  "reasons": ["관찰된 URL 특징이며 모델 기여도 설명이 아닙니다."],
  "model_version": "linkguard-rf-v1"
}
```

위 응답은 형식 예시이며 해당 주소에 대한 실제 판정이 아닙니다.

| 필드 | 계약 |
| --- | --- |
| url | 정규화한 요청 URL과 동일한 문자열 |
| status | safe / caution / danger |
| score | 0~100 정수, 보정된 피싱 확률이 아닌 상대 신호 |
| reasons | 비어 있지 않은 문자열 1~12개, 각 500자 이하 |
| model_version | 비어 있지 않은 버전 문자열, 120자 이하 |

성공 응답은 HTTP 200과 `application/json`입니다. 입력 오류는 400/422, 모델 미준비·사용 불가는 503, 서버 요청 본문 16 KiB 초과는 413으로 처리합니다. Kotlin 클라이언트는 최대 64 KiB 응답을 읽습니다. 실패 시 판정·점수를 만들어 저장하지 않으며 로컬 규칙으로 몰래 대체하지 않습니다.

Python 서버는 Random Forest의 피싱 클래스 출력에 100을 곱해 반올림한 정수 점수를 사용합니다. 40점 미만 safe, 40~79 caution, 80 이상 danger는 검증 전 시제품 표시 기준입니다. Kotlin 로컬 규칙의 32/65점 기준과 다르며 앱은 서버 등급을 그대로 표시합니다. 관찰된 특징 설명은 RF 특징 기여도나 인과관계 계산이 아닙니다.

서버 주소는 쿼리·프래그먼트·사용자 정보가 없는 HTTPS 기본 주소로 설정합니다. 앱은 뒤에 `/predict`를 붙이며 리디렉션을 따라가지 않습니다. 유효한 인증서를 제공하는 HTTPS 리버스 프록시를 구성하세요. 대상 URL 자체에 접속하지 않습니다.
```

## README.md

```text
# LinkGuard 재구성본

이 프로젝트는 **2026-11-18 대화 기록을 바탕으로 다시 작성한 재구성본**입니다. 이전 작업환경의 소스·ZIP·APK 원본은 확보하지 못했으므로 원본과 바이트 단위로 같다고 보장하지 않습니다. 이전 대화의 테스트 23개·50개 통과 결과는 이 재구성본의 검증 결과가 아닙니다.

Kotlin Android 앱과 Python URL 탐지 서버를 제공합니다. 실제 학습 데이터셋과 학습된 운영 모델은 포함하지 않습니다. 논문의 정확도를 LinkGuard의 성능으로 주장하지 않습니다.

## Android 앱

홈, URL 검사, QR 검사, 기록, 설정의 다섯 화면을 Jetpack Compose로 구성합니다. URL 직접 입력·공유·QR과 권한 기반 SMS·알림에서 공통 분석기를 사용합니다. 링크를 자동으로 열거나 클릭을 강제 차단하지 않습니다.

| 항목 | 설정 |
| --- | --- |
| Kotlin / 화면 | 2.0.21 / Jetpack Compose |
| 최소 / 대상 / 컴파일 SDK | 26 / 35 / 35 |
| JDK / Gradle / AGP | 17 / 8.9 / 8.7.3 |

Android Studio에서 이 폴더를 열고 SDK 35와 JDK 17을 설정한 다음 Gradle 동기화를 수행하세요. 터미널에서는 `./gradlew testDebugUnitTest assembleDebug lintDebug`를 실행합니다. Windows에서는 `gradlew.bat`을 사용합니다. 생성되는 개발용 APK 경로는 `app/build/outputs/apk/debug/app-debug.apk`입니다. 실제 빌드 확인 여부는 [검증 기록](docs/IMPLEMENTATION.md)을 확인하세요.

**앱 기본 모드는 로컬 구조 규칙**이며 학습 AI가 아닙니다. 사용자가 HTTPS 서버 주소를 저장하고 서버 분석을 켜면 추출된 URL만 서버에 전송합니다. 문자·알림 전체 본문과 QR 이미지는 전송하지 않습니다. 서버 연결 오류나 모델 없음은 검사 실패로 표시하며 정상 판정으로 바꾸지 않습니다.

SMS와 앱 알림 감지는 기본적으로 꺼져 있습니다. 설정에서 채널을 켜고 필요한 기기 권한을 허용한 뒤 홈에서 보호를 시작하세요. SMS는 새로 수신한 메시지에서만 URL을 추출하며 기존 문자함을 읽지 않습니다. 다른 앱은 알림에 표시된 텍스트만 분석합니다. 경고 게시에는 Android 13 이상의 알림 권한과 알림 채널 허용이 필요합니다. QR은 ZXing 카메라 스캐너를 사용합니다.

기록은 기기에 최대 200건 저장하고 백업에서 제외합니다. 기록 탭에서 삭제할 수 있습니다. 강제 종료, 절전 정책, 권한 회수, 알림 내용 숨김과 방송 수신 시간 제한 때문에 자동 감지는 누락되거나 중단될 수 있습니다. 실기기에서 권한·카메라·수신 동작을 확인해야 합니다. SMS 권한 앱의 스토어 배포 정책 검토는 별도입니다.

## Python 알고리즘과 API

[서버 실행 안내](server/README.md)와 [40개 특징 설명](server/docs/FEATURES.md)을 참고하세요. WDM·RWDM·MAM을 참고한 특징 추출, Random Forest 학습·독립 평가, FastAPI `/predict`를 구현합니다. 실제 URL에 접속하거나 DNS·평판을 조회하지 않습니다.

```sh
cd server
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python detector.py features https://www.example.com
```

[API 계약](API_CONTRACT.md)은 Kotlin과 Python에서 공유합니다. Android 앱은 HTTP 주소를 허용하지 않으므로 운영 연결에는 유효한 인증서가 있는 HTTPS 주소가 필요합니다.

## 보관과 전달

현재 작업환경의 파일은 영구 백업이나 사용자 PC에 저장된 파일을 뜻하지 않습니다. 소스 ZIP을 만들었더라도 실제 내려받기·저장 여부를 따로 확인해야 합니다. 파일 전달 기능이 확인되지 않은 경로를 다운로드 링크라고 안내하지 않습니다. 장기 보관에는 실제 다운로드나 사용자 저장소로의 명시적 내보내기가 필요합니다.

## 이번 재구성본에서 확인한 결과

Python 단위 테스트 40개와 Kotlin JUnit 16개가 통과했습니다. APK 빌드·메타데이터·서명 확인을 통과했으며 Android Lint는 오류 0개, 의존성 새 버전 안내 경고 4개입니다. Python CLI·실제 HTTP 200/422/503·설치 패키지 리소스를 확인했습니다. 합성 데이터 테스트는 실제 피싱 정확도 측정이 아니며, Android 실기기·에뮬레이터·운영 HTTPS 연동은 실행 검증하지 않았습니다. 자세한 기록은 [IMPLEMENTATION](docs/IMPLEMENTATION.md)에 있습니다.
```

## RECONSTRUCTION.json

```json
{
  "kind": "conversation-based reconstruction, NOT byte-identical original recovery",
  "version": "0.2.0-rebuilt",
  "python_unit_tests": 40,
  "kotlin_unit_tests": 16,
  "android_lint_errors": 0,
  "android_lint_update_warnings": 4,
  "live_local_api_statuses_verified": [
    200,
    422,
    503
  ],
  "real_device_tested": false,
  "trained_production_model_included": false,
  "sources": {
    ".gitignore": "b0faf5d11faaa985d57ebe9177f50efa12698706a1efbbf5a77c132c0334a974",
    "API_CONTRACT.md": "01efb819e518a736098da427d620b540e47451550df117f54407a2ff7ed66327",
    "README.md": "0a72a601b06165b462ea126c854f18db2c6c6f0267cea8a1044eddfabdda2239",
    "app/build.gradle.kts": "7ddc03350acfb920a51891e4e116134bb7aef604b86227c7f9fe8bbbad194d25",
    "app/src/main/AndroidManifest.xml": "d4efed13c6734cb34d8d67a08d1aceb1549cc82aa444e12261e56b4146a13783",
    "app/src/main/java/kr/ac/linkguard/LinkGuardApplication.kt": "78c179c2a97bb7ebbe7194d6a1fe3ecd46525accae32a89a7c97b4d681b1c076",
    "app/src/main/java/kr/ac/linkguard/MainActivity.kt": "2d8dea272bed758a0bb614dd699836cf685f6f52ca738776c6b74c78771f2d20",
    "app/src/main/java/kr/ac/linkguard/background/AlertNotifier.kt": "bfd0bc87c2d7e7181419d94034cc2b1be8df8a3869436b98ef7c0c363594a671",
    "app/src/main/java/kr/ac/linkguard/background/LinkNotificationListener.kt": "fadd3d20a1a5bf005bc0992f6a3dd9d48c7d7806ca761147c8496816a04aa872",
    "app/src/main/java/kr/ac/linkguard/background/PermissionHelper.kt": "b0066096e51371eccac87a40c2c802690cf1c4d62f8d04504c0ae75f2e53ec19",
    "app/src/main/java/kr/ac/linkguard/background/SmsReceiver.kt": "8436e0f130bb1e6d3c1b5f1bb611d0534ef48440e873f26c9983b5b22c5ba17b",
    "app/src/main/java/kr/ac/linkguard/background/UrlIntake.kt": "96f42db09aab9ff54f31e533f1cfb2f457bf37f09ec3b51aa49477ffbaef1750",
    "app/src/main/java/kr/ac/linkguard/core/Models.kt": "a537d81ae2a4f90a8dd359a711216392ff87e716d7e563480dcac82d2fc2e806",
    "app/src/main/java/kr/ac/linkguard/core/RuleAnalyzer.kt": "0c8b794b3ebecb637ac84117fc1db35d97f511428f9bcfd16963df05101ff490",
    "app/src/main/java/kr/ac/linkguard/core/UrlTools.kt": "5a25f5fd82065695a9b822f582d196d53b3a337e7c847f2857a8f80643794670",
    "app/src/main/java/kr/ac/linkguard/data/LinkGuardRepository.kt": "449a304ed27f2bca45260d314efc3417a5f09919ab07be3947c3ac13f128c65a",
    "app/src/main/java/kr/ac/linkguard/data/PredictionParser.kt": "919b83e954c0d3cb7952adda00c085cd2fb914ca42c7532594077cc8d3ce6628",
    "app/src/main/java/kr/ac/linkguard/ui/HistoryAndResult.kt": "451e29399aabd770360be0b1b5e48047e1e48ff7c17e24c03b2741fa53d0c3ec",
    "app/src/main/java/kr/ac/linkguard/ui/QrScreen.kt": "6c43b3c68dce6fa7fd6880e8deb2aa62d7a26c86ce1f338c74bc572441e1e281",
    "app/src/main/java/kr/ac/linkguard/ui/Screens.kt": "1b133e9f544843ade21e58e5c72202887ee38be516a9dc8e4153bccb243cb5b4",
    "app/src/main/java/kr/ac/linkguard/ui/Theme.kt": "d50c3905453eb45a4852c1f7474b3c70bc334df2b2efb933bc5d22464201725c",
    "app/src/main/res/drawable/ic_linkguard.xml": "1f82a3ca0d35e122f107cbb348e9f5149cc1bfc8288fc128da2360e6e8e277fc",
    "app/src/main/res/values/styles.xml": "23e500e1a99a699b9d3e79b6e05d83a38179f61dbc9e025a8469f9015b9aadeb",
    "app/src/main/res/xml/data_extraction_rules.xml": "fb4e773c9ddf57df67be9ad1b7368cf775e817327426b44595ed2f96a3548a00",
    "app/src/test/java/kr/ac/linkguard/core/RuleAnalyzerTest.kt": "dacf489ded956bbb8a260ea934224ed1ba7340c4fd89696032b5c071a1156253",
    "app/src/test/java/kr/ac/linkguard/core/UrlToolsTest.kt": "73bb66b7df20def2d892d7fed735ba9ef3169d43bc2d876afe14eacc7016ae4e",
    "app/src/test/java/kr/ac/linkguard/data/PredictionParserTest.kt": "9b1770e947b15e9776ae98f68b199243747c00c84d53353f8a0bb3f3d284d0f6",
    "build.gradle.kts": "61cd8e15a65a3ded440013250aa5c2bbc875158d0cf2db2e8fc5185ec3c69105",
    "docs/IMPLEMENTATION.md": "cef97fb7d727de135650b4eb8117b82316414f613c17b2a4e25cc09a142e3d98",
    "gradle/wrapper/gradle-wrapper.jar": "498495120a03b9a6ab5d155f5de3c8f0d986a449153702fb80fc80e134484f17",
    "gradle/wrapper/gradle-wrapper.properties": "dc0c4f45f299ac2d51077dd1587e619128d091816ad9170d535a23694ddf355b",
    "gradle.properties": "678c35a27eeda302d6a960484179d118d08fb1edf05c1b40745bc7aed6e88f03",
    "gradlew": "a3648413b47ef77af21d5ebc36c687c7d103aaef3e17f33de7d4f080a6f300a3",
    "gradlew.bat": "57931b17dd228e5c24dac90e815d0bf82477e831a4618dfab4136f5446b42a9f",
    "server/README.md": "e9783b58f4db19ca5bd3986a662acbd74a46b1547b3afd5fdf1eec13c01a60fc",
    "server/data/FORMAT.md": "95d73491900740e80281febc4b398c2205ce68a3be25912d0efc0b5928766d36",
    "server/detector.py": "ab9c2b7e048144423c02e5d385961fe32308b55cd314618053af1caa4dbf90f0",
    "server/docs/FEATURES.md": "0160e7e1ada964dd36c73076ec5326cdad55e9a9c2cb3fba4d30db7071122fa7",
    "server/linkguard/__init__.py": "6f2b8a9a5ec5071d9fbad84a0f3d6b88be179182f308a0c2b19cb06519770b14",
    "server/linkguard/features.py": "3b31c3ce08016550c0a0cd84bdbd8c943e4cff070fc7e98a4c0e9211984e6c64",
    "server/linkguard/model.py": "44890d50414619e1da575e74975692f5ffd3dccb55e00809d86a9c45c60fb730",
    "server/linkguard/nlp.py": "ce155d33021dcfe9c9b8778621763cddff57d4d5a40e98dafcf4f03a78452c53",
    "server/linkguard/resources/brands.json": "362822fcce8e877ce53cfdb31f2027173dd9b5d31609af1c4622e3c884ce622d",
    "server/linkguard/resources/corpus.txt": "5b2bd259f01f0bcc04da3d026359e5a800e864f6c4812c30ad42e551461af749",
    "server/linkguard/resources/dictionary.txt": "6c3e35bdccff73f71d56b174a5a0d9ef007b67aee4e94c2a79148653027c2b4d",
    "server/linkguard/resources/keywords.txt": "bc6200a30f33ed9e9a56eeed5c8722c05660f2e152419a880f23580be4724c12",
    "server/linkguard/resources/known_tlds.txt": "26dd2041a4aae62f93c752bd0fde067a5863544de3263be6d85ead36aa29db59",
    "server/linkguard/training.py": "a7d518f4be2168ac60173315d121d152f3988c46d718ee828f3f12b8d9d71f64",
    "server/linkguard/urltools.py": "f82775429260c6c5068e392709f342bf11dbac0780780316226dd6f636036c94",
    "server/pyproject.toml": "c0643d2e594eaad8e27bce16c7b6087d2d36670bb58787138ecfb3684f15dc7e",
    "server/requirements-dev.txt": "934fbb549ab3209320a68f549631f92ffa7dcd1372d15620c148eb5f55bd7735",
    "server/requirements-lock.txt": "e09e6a712ff142992441c0dafbdb6c4aab1c6b417cf99994a0624149cd9b4a40",
    "server/requirements.txt": "4437bbda1f3573c40b39db62f36cd44f4c20fff81d39fe29cbff8b5253764023",
    "server/server.py": "64142fa268c0764e0995a037204d232d7d0f6851705f16bddea2ddfc85cd2d2d",
    "server/tests/test_api.py": "67f47ce8b045b2848750a9f82e4c1c775ae51ed23d5c6b664f910a7d475a5ff8",
    "server/tests/test_features.py": "9ab889da2627c3059f298fd0301bd6e7c90bf3d4a4cc4b1dc104ee463a082895",
    "server/tests/test_training.py": "ab8cd94693d3853aca3d10e1287ec2df72890ae3e1de7f7485833b8cb56eff05",
    "server/tests/test_urltools.py": "ecd09850b0f5ab4c6d529983745d64694c45ecd73a2ac79be6ccccc56f96daeb",
    "server/train.py": "24c0b9ac10d9b253b3f59fbc2afdf349d68f5024ea6a513e915b06c88065063d",
    "settings.gradle.kts": "b66641bfaaaf4fe1bf1af2ddebb6f6d7be9ebf12e4f88678d18e36f6d9b43c39"
  }
}
```

## app/build.gradle.kts

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "kr.ac.linkguard"
    compileSdk = 35
    defaultConfig {
        applicationId = "kr.ac.linkguard"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0-rebuilt"
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
```

## app/src/main/AndroidManifest.xml

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.RECEIVE_SMS" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.telephony" android:required="false" />
    <application android:name=".LinkGuardApplication" android:allowBackup="false" android:fullBackupContent="false"
        android:dataExtractionRules="@xml/data_extraction_rules" android:icon="@drawable/ic_linkguard"
        android:label="LinkGuard" android:supportsRtl="true" android:theme="@style/Theme.LinkGuard"
        android:usesCleartextTraffic="false">
        <activity android:name=".MainActivity" android:exported="true" android:launchMode="singleTop">
            <intent-filter><action android:name="android.intent.action.MAIN" /><category android:name="android.intent.category.LAUNCHER" /></intent-filter>
            <intent-filter><action android:name="android.intent.action.SEND" /><category android:name="android.intent.category.DEFAULT" /><data android:mimeType="text/plain" /></intent-filter>
        </activity>
        <receiver android:name=".background.SmsReceiver" android:exported="true" android:permission="android.permission.BROADCAST_SMS">
            <intent-filter><action android:name="android.provider.Telephony.SMS_RECEIVED" /></intent-filter>
        </receiver>
        <service android:name=".background.LinkNotificationListener" android:exported="true"
            android:label="LinkGuard 알림 URL 감지" android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
            <intent-filter><action android:name="android.service.notification.NotificationListenerService" /></intent-filter>
        </service>
    </application>
</manifest>
```

## app/src/main/java/kr/ac/linkguard/LinkGuardApplication.kt

```kotlin
package kr.ac.linkguard
import android.app.Application
import kr.ac.linkguard.data.LinkGuardRepository
class LinkGuardApplication : Application() { val repository: LinkGuardRepository by lazy { LinkGuardRepository(this) } }
```

## app/src/main/java/kr/ac/linkguard/MainActivity.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/background/AlertNotifier.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/background/LinkNotificationListener.kt

```kotlin
package kr.ac.linkguard.background
import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import kr.ac.linkguard.LinkGuardApplication
import kr.ac.linkguard.core.ScanSource
class LinkNotificationListener : NotificationListenerService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val queue = Channel<String>(16)
    override fun onCreate() {
        super.onCreate()
        scope.launch { for (text in queue) { try { UrlIntake.process(applicationContext, text, ScanSource.NOTIFICATION) } catch (e: CancellationException) { throw e } catch (_: Exception) { AlertNotifier.notifyFailure(applicationContext) } } }
    }
    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn ?: return
        val settings = (application as LinkGuardApplication).repository.settings.value
        if (!settings.protectionEnabled || !settings.notificationEnabled || !PermissionHelper.notificationAccessGranted(this)) return
        if (sbn.packageName == packageName || sbn.isOngoing || sbn.notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return
        val extras = sbn.notification.extras ?: return
        val text = buildString {
            for (key in listOf(Notification.EXTRA_TITLE, Notification.EXTRA_TEXT, Notification.EXTRA_BIG_TEXT)) {
                if (length >= 16_384) break
                extras.getCharSequence(key)?.let { append(it.take(16_384 - length)); append(' ') }
            }
            extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)?.take(20)?.forEach { if (length < 16_384) { append(it.take(16_384 - length)); append(' ') } }
        }.take(16_384)
        if (text.isNotBlank()) queue.trySend(text)
    }
    override fun onDestroy() { queue.close(); scope.cancel(); super.onDestroy() }
}
```

## app/src/main/java/kr/ac/linkguard/background/PermissionHelper.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/background/SmsReceiver.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/background/UrlIntake.kt

```kotlin
package kr.ac.linkguard.background
import android.content.Context
import android.os.SystemClock
import kotlinx.coroutines.CancellationException
import kr.ac.linkguard.LinkGuardApplication
import kr.ac.linkguard.core.*
import java.security.MessageDigest
internal object UrlIntake {
    private val recent = LinkedHashMap<String, Long>()
    private fun reserve(url: String): Boolean = synchronized(recent) {
        val now = SystemClock.elapsedRealtime()
        recent.entries.removeAll { now - it.value >= 60_000 }
        val key = MessageDigest.getInstance("SHA-256").digest(url.toByteArray()).joinToString("") { "%02x".format(it) }
        if (key in recent) return@synchronized false
        while (recent.size >= 256) recent.remove(recent.keys.first())
        recent[key] = now; true
    }
    suspend fun process(context: Context, text: String, source: ScanSource) {
        val repository = (context.applicationContext as LinkGuardApplication).repository
        for (url in UrlTools.extract(text.take(16_384)).take(3)) {
            val config = repository.settings.value
            if (!config.protectionEnabled) return
            if (source == ScanSource.SMS && (!config.smsEnabled || !PermissionHelper.smsGranted(context))) return
            if (source == ScanSource.NOTIFICATION && (!config.notificationEnabled || !PermissionHelper.notificationAccessGranted(context))) return
            if (!reserve(url)) continue
            try { AlertNotifier.notifyResult(context, repository.analyze(url, source)) }
            catch (e: CancellationException) { throw e }
            catch (_: Exception) { AlertNotifier.notifyFailure(context) }
        }
    }
}
```

## app/src/main/java/kr/ac/linkguard/core/Models.kt

```kotlin
package kr.ac.linkguard.core

enum class RiskLevel { LOW, CAUTION, HIGH }
enum class ScanSource(val label: String) { MANUAL("직접 검사"), QR("QR 코드"), SMS("SMS"), NOTIFICATION("앱 알림"), SHARE("공유 링크") }
enum class AnalysisMode { LOCAL_RULES, REMOTE_AI }
data class ScanResult(val id: String, val timestamp: Long, val originalUrl: String, val normalizedUrl: String, val score: Int, val level: RiskLevel, val reasons: List<String>, val source: ScanSource, val mode: AnalysisMode, val modelVersion: String? = null)
```

## app/src/main/java/kr/ac/linkguard/core/RuleAnalyzer.kt

```kotlin
package kr.ac.linkguard.core

import java.net.URI
import java.util.UUID

/** Illustrative local structure rules, not a trained AI classifier. */
class RuleAnalyzer {
    fun analyze(input: String, source: ScanSource = ScanSource.MANUAL): ScanResult {
        val normalized = UrlTools.normalize(input)
        val uri = URI(normalized)
        val authority = uri.rawAuthority
        val host = if (authority.startsWith('[')) authority.substringAfter('[').substringBefore(']') else authority.substringBefore(':')
        val searchable = (host + uri.rawPath.orEmpty() + uri.rawQuery.orEmpty()).lowercase()
        var score = 7
        val reasons = mutableListOf<String>()
        fun add(points: Int, reason: String) { score += points; reasons += reason }
        if (uri.scheme == "http") add(23, "HTTPS가 아닌 HTTP 형식이에요.")
        if (UrlTools.isIpv4(host) || host.contains(':')) add(26, "도메인 이름 대신 IP 주소를 사용해요.")
        if (host.split('.').any { it.startsWith("xn--") }) add(17, "국제화 도메인(Punycode)을 사용해요.")
        if ('-' in host) add(13, "호스트 이름에 하이픈이 포함되어 있어요.")
        if (Regex("login|verify|update|confirm|account|secure|password|delivery|parcel").containsMatchIn(searchable)) add(19, "인증·계정·배송 관련 문자열이 포함되어 있어요.")
        if (normalized.length > 80) add(12, "URL이 80자보다 길어요.")
        if (host.removePrefix("www.") in setOf("bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly")) add(17, "단축 URL 형태예요. 최종 목적지는 확인하지 않았어요.")
        if (host.any { it.isDigit() }) add(7, "호스트 이름에 숫자가 포함되어 있어요.")
        if (reasons.isEmpty()) reasons += "로컬 규칙에서 두드러지는 의심 패턴을 찾지 못했어요."
        score = score.coerceAtMost(99)
        return ScanResult(UUID.randomUUID().toString(), System.currentTimeMillis(), input.trim(), normalized, score, levelForScore(score), reasons, source, AnalysisMode.LOCAL_RULES)
    }
    companion object {
        fun levelForScore(score: Int): RiskLevel = when { score >= 65 -> RiskLevel.HIGH; score >= 32 -> RiskLevel.CAUTION; else -> RiskLevel.LOW }
    }
}
```

## app/src/main/java/kr/ac/linkguard/core/UrlTools.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/data/LinkGuardRepository.kt

```kotlin
package kr.ac.linkguard.data

import android.content.Context
import kr.ac.linkguard.core.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

data class AppSettings(val protectionEnabled: Boolean = false, val smsEnabled: Boolean = false, val notificationEnabled: Boolean = false, val warningEnabled: Boolean = true, val remoteEnabled: Boolean = false, val serverUrl: String = "")

class LinkGuardRepository(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("linkguard_private", Context.MODE_PRIVATE)
    private val lock = Any()
    private val mutableHistory = MutableStateFlow(readHistory())
    val history: StateFlow<List<ScanResult>> = mutableHistory.asStateFlow()
    private val mutableSettings = MutableStateFlow(readSettings())
    val settings: StateFlow<AppSettings> = mutableSettings.asStateFlow()
    fun updateSettings(transform: (AppSettings) -> AppSettings) = synchronized(lock) {
        val next = transform(mutableSettings.value)
        require(next.serverUrl.length <= 2048) { "서버 주소가 너무 길어요." }
        if (next.serverUrl.isNotBlank()) validateBase(next.serverUrl)
        require(!next.remoteEnabled || next.serverUrl.isNotBlank()) { "먼저 서버 주소를 저장해 주세요." }
        prefs.edit().putString("settings", JSONObject().apply {
            put("protectionEnabled", next.protectionEnabled); put("smsEnabled", next.smsEnabled); put("notificationEnabled", next.notificationEnabled)
            put("warningEnabled", next.warningEnabled); put("remoteEnabled", next.remoteEnabled); put("serverUrl", next.serverUrl)
        }.toString()).apply()
        mutableSettings.value = next
    }
    suspend fun analyze(input: String, source: ScanSource = ScanSource.MANUAL): ScanResult = withContext(Dispatchers.IO) {
        val normalized = UrlTools.normalize(input)
        val config = settings.value
        val result = if (config.remoteEnabled) remote(input.trim(), normalized, source, config.serverUrl) else RuleAnalyzer().analyze(input, source)
        currentCoroutineContext().ensureActive()
        synchronized(lock) {
            mutableHistory.value = (listOf(result) + mutableHistory.value).take(200)
            persistHistory()
        }
        result
    }
    fun clearHistory() = synchronized(lock) { mutableHistory.value = emptyList(); prefs.edit().remove("history").apply() }
    fun findResult(id: String): ScanResult? = history.value.firstOrNull { it.id == id }
    private fun persistHistory() {
        val array = JSONArray()
        history.value.forEach { r -> array.put(JSONObject().apply {
            put("id", r.id); put("timestamp", r.timestamp); put("originalUrl", r.originalUrl); put("normalizedUrl", r.normalizedUrl)
            put("score", r.score); put("level", r.level.name); put("reasons", JSONArray(r.reasons)); put("source", r.source.name); put("mode", r.mode.name)
            r.modelVersion?.let { put("modelVersion", it) }
        }) }
        prefs.edit().putString("history", array.toString()).apply()
    }
    private fun readSettings(): AppSettings = runCatching {
        val j = JSONObject(prefs.getString("settings", "{}") ?: "{}")
        AppSettings(j.optBoolean("protectionEnabled"), j.optBoolean("smsEnabled"), j.optBoolean("notificationEnabled"), j.optBoolean("warningEnabled", true), j.optBoolean("remoteEnabled"), j.optString("serverUrl").take(2048))
    }.getOrDefault(AppSettings())
    private fun readHistory(): List<ScanResult> = runCatching {
        val a = JSONArray(prefs.getString("history", "[]") ?: "[]")
        (0 until minOf(a.length(), 200)).mapNotNull { i -> runCatching {
            val j = a.getJSONObject(i); val r = j.getJSONArray("reasons")
            ScanResult(j.getString("id"), j.getLong("timestamp"), j.getString("originalUrl"), j.getString("normalizedUrl"), j.getInt("score").also { require(it in 0..100) }, RiskLevel.valueOf(j.getString("level")), (0 until r.length()).map { r.getString(it) }, ScanSource.valueOf(j.getString("source")), AnalysisMode.valueOf(j.getString("mode")), if (j.has("modelVersion")) j.getString("modelVersion") else null)
        }.getOrNull() }
    }.getOrDefault(emptyList())
    private fun validateBase(value: String): String {
        val normalized = UrlTools.normalize(value.trim()); val uri = URI(normalized)
        require(uri.scheme == "https" && uri.rawQuery == null && uri.rawFragment == null) { "쿼리·프래그먼트 없는 HTTPS 서버 주소를 입력해 주세요." }
        return normalized.trimEnd('/')
    }
    private fun remote(original: String, normalized: String, source: ScanSource, base: String): ScanResult {
        val connection = URL(validateBase(base) + "/predict").openConnection() as HttpURLConnection
        connection.apply { requestMethod = "POST"; connectTimeout = 10_000; readTimeout = 15_000; instanceFollowRedirects = false; doOutput = true; setRequestProperty("Content-Type", "application/json; charset=utf-8"); setRequestProperty("Accept", "application/json") }
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(25)
        val watchdog = scheduler.schedule({ connection.disconnect() }, 25, TimeUnit.SECONDS)
        fun timeout(): Int {
            val remaining = TimeUnit.NANOSECONDS.toMillis(deadline - System.nanoTime())
            if (remaining <= 0) throw java.net.SocketTimeoutException()
            return remaining.coerceAtMost(15_000).toInt().coerceAtLeast(1)
        }
        try {
            val request = JSONObject().put("url", normalized).toString().toByteArray(Charsets.UTF_8)
            connection.setFixedLengthStreamingMode(request.size); connection.outputStream.use { it.write(request) }; connection.readTimeout = timeout()
            when (val code = connection.responseCode) {
                200 -> Unit
                400, 422 -> error("AI 서버가 URL 입력을 거부했어요.")
                503 -> error("AI 서버에 학습된 모델이 준비되지 않았거나 요청이 많아요.")
                401, 403 -> error("AI 서버 접근 권한을 확인해 주세요.")
                in 300..399 -> error("서버 주소가 이동했어요. 설정을 확인해 주세요.")
                else -> error("AI 서버 오류가 발생했어요. (HTTP $code)")
            }
            require(connection.contentType.orEmpty().substringBefore(';').trim().equals("application/json", true)) { "AI 서버 응답이 JSON이 아니에요." }
            val response = connection.inputStream.use { stream ->
                val out = ByteArrayOutputStream(); val buffer = ByteArray(4096)
                while (true) { connection.readTimeout = timeout(); val count = stream.read(buffer); if (count < 0) break; require(out.size() + count <= 65536) { "서버 응답이 너무 커요." }; out.write(buffer, 0, count) }
                out.toByteArray().toString(Charsets.UTF_8)
            }
            return PredictionParser.parse(response, original, normalized, source)
        } catch (e: java.net.SocketTimeoutException) { throw IllegalStateException("AI 서버 응답 시간이 초과됐어요.", e)
        } catch (e: javax.net.ssl.SSLException) { throw IllegalStateException("AI 서버 HTTPS 인증서를 확인할 수 없어요.", e)
        } catch (e: IOException) { throw IllegalStateException("AI 서버 연결을 확인해 주세요.", e)
        } finally { watchdog.cancel(false); connection.disconnect() }
    }
    companion object { private val scheduler = Executors.newSingleThreadScheduledExecutor { r -> Thread(r, "linkguard-request-deadline").apply { isDaemon = true } } }
}
```

## app/src/main/java/kr/ac/linkguard/data/PredictionParser.kt

```kotlin
package kr.ac.linkguard.data

import kr.ac.linkguard.core.*
import org.json.JSONObject
import org.json.JSONTokener
import java.util.UUID

internal object PredictionParser {
    fun parse(body: String, original: String, normalized: String, source: ScanSource): ScanResult {
        try {
            val tokener = JSONTokener(body)
            val json = tokener.nextValue() as? JSONObject ?: error("object")
            require(tokener.nextClean() == '\u0000')
            require(UrlTools.normalize(json.get("url") as? String ?: error("url")) == normalized)
            val level = when (json.get("status")) { "safe" -> RiskLevel.LOW; "caution" -> RiskLevel.CAUTION; "danger" -> RiskLevel.HIGH; else -> error("status") }
            val score = when (val raw = json.get("score")) { is Int -> raw; is Long -> raw.also { require(it in 0L..100L) }.toInt(); else -> error("integer") }.also { require(it in 0..100) }
            val array = json.getJSONArray("reasons"); require(array.length() in 1..12)
            val reasons = (0 until array.length()).map { (array.get(it) as? String ?: error("reason")).trim().also { text -> require(text.isNotBlank() && text.length <= 500) } }
            val version = (json.get("model_version") as? String ?: error("version")).trim()
            require(version.isNotBlank() && version.length <= 120 && version.none { it.code < 32 || it.code == 127 })
            return ScanResult(UUID.randomUUID().toString(), System.currentTimeMillis(), original, normalized, score, level, reasons, source, AnalysisMode.REMOTE_AI, version)
        } catch (e: Exception) { throw IllegalStateException("AI 서버 응답이 연동 규격과 맞지 않아요.", e) }
    }
}
```

## app/src/main/java/kr/ac/linkguard/ui/HistoryAndResult.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/ui/QrScreen.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/ui/Screens.kt

```kotlin
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
```

## app/src/main/java/kr/ac/linkguard/ui/Theme.kt

```kotlin
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
```

## app/src/main/res/drawable/ic_linkguard.xml

```xml
<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="48dp" android:height="48dp" android:viewportWidth="48" android:viewportHeight="48">
    <path android:fillColor="#153D40" android:pathData="M0,0h48v48h-48z"/>
    <path android:fillColor="#65ECCD" android:pathData="M24,6L9,12v11c0,9 6.4,16.8 15,19 8.6,-2.2 15,-10 15,-19V12z"/>
    <path android:fillColor="#153D40" android:pathData="M21,30L14,23l3,-3 4,4 10,-10 3,3z"/>
</vector>
```

## app/src/main/res/values/styles.xml

```xml
<resources>
    <style name="Theme.LinkGuard" parent="android:style/Theme.Material.NoActionBar">
        <item name="android:fontFamily">sans</item>
        <item name="android:windowLightStatusBar">false</item>
        <item name="android:statusBarColor">#0B1523</item>
        <item name="android:navigationBarColor">#101E2D</item>
    </style>
</resources>
```

## app/src/main/res/xml/data_extraction_rules.xml

```xml
<data-extraction-rules>
    <cloud-backup><exclude domain="root" path="."/><exclude domain="sharedpref" path="."/></cloud-backup>
    <device-transfer><exclude domain="root" path="."/><exclude domain="sharedpref" path="."/></device-transfer>
</data-extraction-rules>
```

## app/src/test/java/kr/ac/linkguard/core/RuleAnalyzerTest.kt

```kotlin
package kr.ac.linkguard.core
import org.junit.Assert.*
import org.junit.Test
class RuleAnalyzerTest {
    private val analyzer = RuleAnalyzer()
    @Test fun localProvenanceAndLowSignalDoNotClaimAi() {
        val result = analyzer.analyze("https://example.com", ScanSource.QR)
        assertEquals(AnalysisMode.LOCAL_RULES, result.mode); assertEquals(ScanSource.QR, result.source); assertEquals(RiskLevel.LOW, result.level); assertNotNull(result.id); assertTrue(result.reasons.isNotEmpty())
    }
    @Test fun riskyStructureProducesObservableReasons() {
        val result = analyzer.analyze("http://parcel-delivery-verify.example/login")
        assertEquals(RiskLevel.CAUTION, result.level); assertTrue(result.reasons.any { "HTTP" in it }); assertTrue(result.reasons.size >= 3)
        assertEquals(RiskLevel.HIGH, analyzer.analyze("http://192.0.2.10/verify").level)
    }
    @Test fun scoreBoundariesAreExplicitDemoRules() {
        assertEquals(RiskLevel.LOW, RuleAnalyzer.levelForScore(31)); assertEquals(RiskLevel.CAUTION, RuleAnalyzer.levelForScore(32)); assertEquals(RiskLevel.CAUTION, RuleAnalyzer.levelForScore(64)); assertEquals(RiskLevel.HIGH, RuleAnalyzer.levelForScore(65))
    }
    @Test fun shortenerMatchesExactHostNotSubstring() {
        assertTrue(analyzer.analyze("https://bit.ly/a").reasons.any { "단축" in it })
        assertFalse(analyzer.analyze("https://notbit.ly.example/a").reasons.any { "단축" in it })
    }
    @Test fun numericLeadingDomainLabelCannotCrashUriHostParsing() { assertEquals("https://foo.1a", analyzer.analyze("https://foo.1a").normalizedUrl) }
}
```

## app/src/test/java/kr/ac/linkguard/core/UrlToolsTest.kt

```kotlin
package kr.ac.linkguard.core
import org.junit.Assert.*
import org.junit.Test
class UrlToolsTest {
    @Test fun normalizedHostRetainsPathQueryFragment() {
        assertEquals("https://example.com/Path?q=A%2FB#f", UrlTools.normalize(" EXAMPLE.com/Path?q=A%2FB#f "))
        assertEquals("http://example.com:8080/a", UrlTools.normalize("HTTP://Example.com:8080/a"))
        assertEquals("https://example.com?#", UrlTools.normalize("example.com?#"))
    }
    @Test fun idnAndNumericLiterals() {
        assertEquals("https://xn--bcher-kva.de", UrlTools.normalize("https://bücher.de"))
        assertEquals("https://[2001:db8::1]:443/a", UrlTools.normalize("https://[2001:DB8::1]:443/a"))
        assertEquals("https://192.0.2.10", UrlTools.normalize("192.0.2.10"))
    }
    @Test fun rejectsUnsafeMalformedAndOverlongInput() {
        listOf("javascript:alert(1)", "ftp://example.com", "//example.com", "https:example.com", "https://a:b@example.com", "https://example.com\\@evil.example", "https://example.com\n", "https://bad..example", "https://999.1.1.1", "https://01.2.3.4", "https://localhost", "https://example.com:0", "https://example.com:65536", "https://[2001:::1]", "https://example.com/%gg", "https://example.com/" + "x".repeat(4096)).forEach { assertTrue(it, runCatching { UrlTools.normalize(it) }.isFailure) }
    }
    @Test fun extractsOnlyExplicitValidatedUniqueUrls() {
        assertEquals(listOf("https://example.com/a", "http://example.org?q=1"), UrlTools.extract("주소 (https://example.com/a), https://example.com/a HTTP://example.org?q=1. https://bad..example"))
        assertTrue(UrlTools.extract("example.com").isEmpty())
        assertEquals(20, UrlTools.extract((1..25).joinToString(" ") { "https://example.com/$it" }).size)
    }
    @Test fun utf16LimitAndSurrogatesMatchServerConstraints() {
        val good = "https://example.com/" + "😀".repeat(100)
        assertEquals(good, UrlTools.normalize(good))
        assertTrue(runCatching { UrlTools.normalize("https://example.com/" + "😀".repeat(2100)) }.isFailure)
        assertTrue(runCatching { UrlTools.normalize("https://example.com/" + '\uD800') }.isFailure)
    }
    @Test fun balancedParenthesesAndIpv6Preserved() {
        assertEquals(listOf("https://[2001:db8::1]", "https://example.com/a(b)"), UrlTools.extract("[https://[2001:db8::1]] (https://example.com/a(b))"))
    }
}
```

## app/src/test/java/kr/ac/linkguard/data/PredictionParserTest.kt

```kotlin
package kr.ac.linkguard.data
import kr.ac.linkguard.core.*
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
class PredictionParserTest {
    private fun body(): JSONObject = JSONObject().put("url", "https://example.com").put("status", "safe").put("score", 18).put("reasons", listOf("관찰 특징")).put("model_version", "rf-test")
    private fun parse(text: String) = PredictionParser.parse(text, "example.com", "https://example.com", ScanSource.MANUAL)
    @Test fun validatesRealContractAndKeepsServerGrade() {
        val r = parse(body().put("status", "danger").put("score", 1).toString())
        assertEquals(RiskLevel.HIGH, r.level); assertEquals(1, r.score); assertEquals(AnalysisMode.REMOTE_AI, r.mode); assertEquals("rf-test", r.modelVersion)
    }
    @Test fun rejectsWrongUrlAndUnknownStatus() {
        assertTrue(runCatching { parse(body().put("url", "https://elsewhere.example").toString()) }.isFailure)
        assertTrue(runCatching { parse(body().put("status", "unknown").toString()) }.isFailure)
    }
    @Test fun rejectsNonIntegerScoresAndOutOfRange() {
        listOf<Any>("18", true, 18.5, -1, 101).forEach { assertTrue(runCatching { parse(body().put("score", it).toString()) }.isFailure) }
        assertTrue(runCatching { parse(body().toString().replace("\"score\":18", "\"score\":18.0")) }.isFailure)
    }
    @Test fun rejectsMissingOrUnboundedReasonsAndVersion() {
        for (key in listOf("model_version", "reasons")) { val j = body(); j.remove(key); assertTrue(runCatching { parse(j.toString()) }.isFailure) }
        assertTrue(runCatching { parse(body().put("reasons", emptyList<String>()).toString()) }.isFailure)
        assertTrue(runCatching { parse(body().put("model_version", "x".repeat(121)).toString()) }.isFailure)
    }
    @Test fun rejectsNonObjectsAndTrailingGarbage() { for (text in listOf("[]", "null", "not json", body().toString() + "trailing")) assertTrue(runCatching { parse(text) }.isFailure) }
}
```

## build.gradle.kts

```kotlin
plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}
```

## gradle/wrapper/gradle-wrapper.properties

```text
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionSha256Sum=d725d707bfabd4dfdc958c624003b3c80accc03f7037b5122c4b1d0ef15cecab
distributionUrl=https\://services.gradle.org/distributions/gradle-8.9-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
```

## gradle.properties

```text
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
```

## server/README.md

```text
# LinkGuard Python 재구성본

대화 기록을 바탕으로 재작성한 URL 특징 추출·Random Forest 학습·FastAPI 서버입니다. 원본 파일의 동일 복원이 아니며 실제 학습 데이터와 기본 학습 모델을 포함하지 않습니다. 논문의 정확도를 재현했다고 주장하지 않습니다.

## 설치와 모델 없는 실행

Python 3.11 이상을 사용하고 이 `server` 폴더에서 실행하세요.

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python detector.py features https://www.example.com
```

검증 환경의 전체 실행·테스트 의존성을 같은 버전으로 설치하려면 `python -m pip install -r requirements-lock.txt`를 사용할 수 있습니다. 이 목록에는 서식 도구 Black을 포함하지 않습니다.

특징 추출은 학습 모델 없이 사용할 수 있습니다. 키워드·HTTP·브랜드 유사어 하나만으로 피싱을 확정하지 않습니다. 분석 중 대상 웹사이트, DNS나 외부 평판 서비스에 접속하지 않으며 PSL과 언어 자료는 로컬 자료를 사용합니다.

## 학습

직접 수집하고 라벨을 검증한 UTF-8 `url,label` CSV를 준비하세요. 정상은 0, 피싱은 1입니다. [형식 안내](data/FORMAT.md)의 예시는 학습용 데이터셋이 아닙니다.

```sh
python train.py --csv data/urls.csv --output artifacts/linkguard.joblib \
  --report artifacts/metrics.json --cv-folds 2 --model-version linkguard-rf-v1
```

옵션은 `--csv`(필수), `--output`(artifacts/linkguard.joblib), `--report`(artifacts/metrics.json), `--cv-folds`(0: 생략, 또는 2~10), `--seed`(42), `--test-size`(0.2), `--trees`(200), `--model-version`(선택)입니다. 중복 제거 후 최소 20개 URL, 라벨별 최소 5개 샘플과 4개 등록 도메인 그룹이 필요합니다. 이는 프로그램의 최소 조건이며 신뢰할 만한 성능 평가에 충분하다는 뜻은 아닙니다. test-size는 0.1~0.5, trees는 10~2000 범위입니다. 모델 버전은 영숫자로 시작하는 최대 120자의 영숫자·점·밑줄·하이픈 문자열이어야 합니다.

중복 제거와 라벨 충돌 검사 후 등록 도메인별로 학습·보류 평가를 나눕니다. 교차 검증은 훈련 부분에만 적용하며 저장 모델은 보류 평가셋으로 재학습하지 않습니다. 보고서에는 정확도, 정밀도, 재현율, F1, 오탐률, 혼동행렬과 분할 정보를 기록합니다. 보고서 `holdout`과 교차 검증은 RF 이진 `predict` 결과를 평가합니다. 별도 `warning_policy_holdout`의 `40`, `80`은 API와 같은 반올림 정수 점수의 >=40 및 >=80 정책을 각각 이진 지표로 평가합니다. 이진 RF 분류 지표와 화면의 세 등급 기준은 다릅니다. 등록 도메인 분리만으로 시간·공격 캠페인·템플릿 누출까지 제거하지는 못합니다.

```sh
python detector.py predict https://www.example.com --model artifacts/linkguard.joblib
```

`joblib`은 Python 객체를 로드하므로 직접 생성하거나 신뢰하는 모델 파일만 사용하세요. 서버는 특징 순서·스키마·리소스 지문·scikit-learn 환경의 호환성을 검사합니다. 잘못된 모델을 정상 판정으로 대체하지 않습니다.

## 서버와 Android 연결

```sh
uvicorn server:app --host 127.0.0.1 --port 8000 --no-access-log
```

다른 모델은 `LINKGUARD_MODEL_PATH` 환경 변수로 경로를 지정합니다. 모델은 시작 시 로드하므로 교체 후 재시작하세요. `/health`에서 사용 가능 상태를 확인합니다. 모델이 없으면 `/predict`는 503을 반환합니다. 동시에 처리하는 추론 한도는 4개이며 한도가 찬 요청은 503으로 안내합니다.

```sh
curl -i http://127.0.0.1:8000/predict -H 'Content-Type: application/json' \
  --data '{"url":"https://www.example.com"}'
```

[공통 API 계약](../API_CONTRACT.md)에 따라 URL·상태·정수 점수·관찰 근거·모델 버전을 반환합니다. score는 보정되지 않은 상대 신호이며 safe<40, caution40~79, danger>=80의 시제품 기준을 사용합니다. 표시 근거는 실제 모델 기여도 분석이 아닙니다.

HTTP 개발 주소를 Android 앱 설정에 그대로 넣을 수 없습니다. 유효한 인증서가 있는 HTTPS 리버스 프록시와 기기에서 접근 가능한 주소를 준비하세요. `127.0.0.1`은 Android에서는 기기 자신입니다. 인증서 검증이나 앱의 평문 통신 제한을 끄지 않습니다. 운영용 인증·접근 제어·보관 정책과 배포는 별도입니다.

요청은 URL 필드만 사용하고 문자·알림 전체 본문과 QR 이미지를 보내지 않습니다. 서버 본문 한도는 16 KiB입니다. 입력 오류는 422, 본문 초과는 413, 모델 미준비나 처리 불가는 503으로 응답합니다.

## 연구 참고와 한계

Sahingoz 외 (2019), Machine learning based phishing detection from URLs, ESWA117:345–357, DOI 10.1016/j.eswa.2018.09.029를 참고했습니다. WDM·RWDM·MAM의 로컬 구현과 40개 특징 정의는 [FEATURES](docs/FEATURES.md)에 있습니다. 원 논문의 사전·코드·데이터·Weka 실험을 복제하지 않았습니다. XGBoost, 사이트 내용·평판 조회와 논문 정확도 재현은 구현 범위가 아닙니다.

## 검증 상태

재구성본을 Python 3.12.14의 새 가상환경에 설치하고 `pip check`를 통과했습니다. 현재 단위 테스트 40개(NLP·특징 14 / URL 7 / 학습 8 / 모델·API 11)가 통과했습니다. 특징 CLI, 합성 URL 80개를 사용한 학습·훈련 내부 2-fold CV·모델/보고서 저장·CLI 예측을 확인했고 실제 Uvicorn TCP 서버에서 정상 200, 입력 오류 422, 모델 미준비 503을 확인했습니다. Python wheel 빌드와 별도 위치에 설치한 패키지의 모듈·언어 리소스 로딩도 확인했습니다. 상세 결과는 [구현 기록](../docs/IMPLEMENTATION.md)에 있습니다. 이전 대화의 통과 수치나 합성 테스트 지표를 실제 탐지 정확도로 표시하지 않습니다. Android 기기·운영 HTTPS 연결과 실제 라벨 데이터 성능 평가는 별도로 필요합니다.
```

## server/detector.py

```python
import argparse, json, sys
from pathlib import Path
from linkguard.features import FeatureExtractor, FEATURE_SCHEMA_VERSION
from linkguard.urltools import normalize_url


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("features")
    a.add_argument("url")
    a = sub.add_parser("predict")
    a.add_argument("url")
    a.add_argument("--model", type=Path, default=Path("artifacts/linkguard.joblib"))
    a = p.parse_args(argv)
    try:
        url = normalize_url(a.url)
        if a.command == "features":
            e = FeatureExtractor()
            result = {
                "url": url,
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "features": e.extract(url),
                "observations": e.explain(url),
                "notice": "특징 관찰이며 피싱 판정이나 모델 기여도 설명이 아닙니다.",
            }
        else:
            from linkguard.model import URLDetector

            result = URLDetector.load(a.model).predict(url)
    except (ValueError, RuntimeError, OSError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## server/linkguard/__init__.py

```python
"""LinkGuard reconstruction, 2026-11-18. No model is shipped or auto-trained."""

__version__ = "0.2.0-rebuilt"
```

## server/linkguard/features.py

```python
"""Rebuilt 40-feature URL extractor adapted from Sahingoz et al. Table 2.

The first 38 categories use explicit local semantics. Alexa's two unavailable
positions are replaced by HTTPS/IP flags. This is not a paper reproduction.
"""

from __future__ import annotations

import hashlib
from importlib import resources
import math
import statistics
from urllib.parse import urlsplit
import tldextract

from .nlp import (
    BRANDS,
    DICTIONARY,
    KEYWORDS,
    KNOWN_TLDS,
    OFFICIAL_DOMAINS,
    RESOURCE_DIR,
    decompose,
    is_random_word,
    letters_only,
    raw_tokens,
    similar_matches,
)
from .urltools import parse_url

FEATURE_SCHEMA_VERSION = "sahingoz-adapted-v1-rebuilt"
FEATURE_NAMES = (
    "raw_word_count",
    "brand_check_domain",
    "average_word_length",
    "longest_word_length",
    "shortest_word_length",
    "word_length_std",
    "adjacent_word_count",
    "average_adjacent_word_length",
    "separated_word_count",
    "keyword_count",
    "brand_name_count",
    "similar_keyword_count",
    "similar_brand_name_count",
    "random_word_count",
    "target_brand_name_count",
    "target_keyword_count",
    "other_word_count",
    "digit_count_domain",
    "digit_count_subdomain",
    "digit_count_path",
    "subdomain_count",
    "random_domain",
    "length_domain",
    "length_subdomain",
    "length_path",
    "known_tld",
    "www_in_domain_subdomain",
    "com_in_domain_subdomain",
    "punycode",
    "count_hyphen",
    "count_dot",
    "count_slash",
    "count_at",
    "count_question",
    "count_ampersand",
    "count_equal",
    "count_underscore",
    "consecutive_character_repeat",
    "uses_https",
    "host_is_ip",
)


def _fingerprint():
    digest = hashlib.sha256()
    digest.update(FEATURE_SCHEMA_VERSION.encode() + b"\0" + tldextract.__version__.encode() + b"\0")
    digest.update(
        hashlib.sha256(
            resources.files("tldextract").joinpath(".tld_set_snapshot").read_bytes()
        ).digest()
    )
    for path in sorted(RESOURCE_DIR.iterdir()):
        if path.is_file() and not path.name.startswith("."):
            digest.update(path.name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


RESOURCE_FINGERPRINT = _fingerprint()


class FeatureExtractor:
    """Pure URL-string analysis with stable feature order and finite float values.

    Domain digits/length use the main registrable label, excluding suffix; path
    includes query and excludes fragment. Raw tokens omit scheme/fragment. Special
    character/repeat counts use the full normalized URL. No feature grants trust.
    """

    def extract(self, url: str) -> dict[str, float]:
        parsed = parse_url(url)
        raw = raw_tokens(parsed.hostname + parsed.path_query)
        lengths = [len(x) for x in raw]
        decomposed = [(letters_only(word), decompose(word)) for word in raw]
        compounds = [(word, parts) for word, parts in decomposed if len(parts) > 1]
        all_words = tuple(part for _, parts in decomposed for part in parts)
        random_words = tuple(word for word in all_words if is_random_word(word))
        words = tuple(word for word in all_words if not is_random_word(word))
        target = tuple(
            part
            for word in raw_tokens(parsed.domain_label)
            for part in decompose(word)
            if not is_random_word(part)
        )
        labels = (
            []
            if parsed.is_ip
            else (
                [*parsed.subdomain.split("."), parsed.domain_label]
                if parsed.subdomain
                else [parsed.domain_label]
            )
        )
        full = parsed.normalized
        values = (
            len(raw),
            int(parsed.registered_domain in OFFICIAL_DOMAINS),
            statistics.mean(lengths) if lengths else 0,
            max(lengths, default=0),
            min(lengths, default=0),
            statistics.pstdev(lengths) if lengths else 0,
            len(compounds),
            statistics.mean([len(word) for word, _ in compounds]) if compounds else 0,
            sum(len(parts) for _, parts in compounds),
            sum(word in KEYWORDS for word in words),
            sum(word in BRANDS for word in words),
            sum(bool(similar_matches(word, KEYWORDS)) for word in words),
            sum(bool(similar_matches(word, BRANDS)) for word in words),
            len(random_words),
            sum(word in BRANDS for word in target),
            sum(word in KEYWORDS for word in target),
            sum(
                word in DICTIONARY and word not in KEYWORDS and word not in BRANDS for word in words
            ),
            sum(x.isascii() and x.isdigit() for x in parsed.domain_label),
            sum(x.isascii() and x.isdigit() for x in parsed.subdomain),
            sum(x.isascii() and x.isdigit() for x in parsed.path_query),
            len(parsed.subdomain.split(".")) if parsed.subdomain else 0,
            int(not parsed.is_ip and is_random_word(parsed.domain_label)),
            len(parsed.domain_label),
            len(parsed.subdomain),
            len(parsed.path_query),
            int(
                bool(parsed.suffix)
                and (parsed.suffix in KNOWN_TLDS or parsed.suffix.rsplit(".", 1)[-1] in KNOWN_TLDS)
            ),
            labels.count("www"),
            labels.count("com"),
            int(any(x.startswith("xn--") for x in parsed.hostname.split("."))),
            *(full.count(x) for x in "-./@?&=_"),
            sum(a == b and a.isalnum() for a, b in zip(full, full[1:])),
            int(urlsplit(full).scheme == "https"),
            int(parsed.is_ip),
        )
        if len(values) != len(FEATURE_NAMES):
            raise RuntimeError("Feature schema mismatch")
        result = dict(zip(FEATURE_NAMES, map(float, values)))
        if not all(math.isfinite(value) for value in result.values()):
            raise RuntimeError("Non-finite feature")
        return result

    def vector(self, url: str) -> list[float]:
        features = self.extract(url)
        return [features[name] for name in FEATURE_NAMES]

    def explain(self, url: str) -> list[str]:
        """Observed indicators only, not RF contribution or causality explanations."""
        parsed = parse_url(url)
        values = self.extract(parsed.normalized)
        reasons = []
        for key, message in [
            ("host_is_ip", "도메인 이름 대신 IP 주소를 사용해요."),
            ("punycode", "국제화 도메인(Punycode) 문자열이 포함되어 있어요."),
            ("keyword_count", "로컬 목록의 계정·인증·배송 관련 단어가 포함되어 있어요."),
            (
                "brand_name_count",
                "로컬 브랜드 목록과 일치하는 단어가 있어요. 소유권을 확인한 것은 아니에요.",
            ),
            ("similar_keyword_count", "편집 거리 기준으로 키워드와 유사한 단어가 있어요."),
            ("similar_brand_name_count", "편집 거리 기준으로 브랜드 이름과 유사한 단어가 있어요."),
            ("random_word_count", "실험용 문자쌍 모델에서 낮은 점수를 받은 단어가 있어요."),
        ]:
            if values[key]:
                reasons.append(message)
        if not values["uses_https"]:
            reasons.insert(0, "HTTPS가 아닌 HTTP URL이에요.")
        if "-" in parsed.hostname:
            reasons.append("호스트 이름에 하이픈이 포함되어 있어요.")
        if values["digit_count_domain"] + values["digit_count_subdomain"]:
            reasons.append("호스트 이름에 숫자가 포함되어 있어요.")
        if len(parsed.normalized) > 80:
            reasons.append("정규화한 URL이 80자보다 길어요.")
        if values["subdomain_count"] >= 3:
            reasons.append("등록 도메인 앞에 하위 도메인이 3개 이상 있어요.")
        return reasons[:12] or [
            "URL 문자열의 40개 특징을 분석했어요. 사이트 내용과 평판은 조회하지 않았어요."
        ]
```

## server/linkguard/model.py

```python
"""Trusted local joblib loading only: pickle is not a sandbox for uploads."""

from pathlib import Path
import re, warnings
import joblib, numpy as np, sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.utils.validation import check_is_fitted
from .features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT, FeatureExtractor
from .urltools import normalize_url


class ModelUnavailableError(RuntimeError):
    pass


class URLDetector:
    def __init__(self, model, version):
        self.model = model
        self.model_version = version
        self.extractor = FeatureExtractor()

    @classmethod
    def load(cls, path):
        try:
            p = Path(path)
            if not p.is_file() or not 0 < p.stat().st_size <= 256 * 1024 * 1024:
                raise ValueError()
            with warnings.catch_warnings():
                warnings.simplefilter("error", InconsistentVersionWarning)
                a = joblib.load(p)
            if (
                not isinstance(a, dict)
                or type(a.get("artifact_version")) != int
                or a["artifact_version"] != 1
            ):
                raise ValueError()
            if (
                a.get("feature_names") != list(FEATURE_NAMES)
                or a.get("feature_schema_version") != FEATURE_SCHEMA_VERSION
                or a.get("resource_fingerprint") != RESOURCE_FINGERPRINT
            ):
                raise ValueError()
            if (
                a.get("thresholds") != {"caution": 40, "danger": 80}
                or a.get("metadata", {}).get("sklearn_version") != sklearn.__version__
            ):
                raise ValueError()
            version = a.get("model_version")
            if not isinstance(version, str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", version
            ):
                raise ValueError()
            m = a.get("model")
            if not isinstance(m, RandomForestClassifier):
                raise ValueError()
            check_is_fitted(m)
            if (
                m.n_features_in_ != len(FEATURE_NAMES)
                or m.n_outputs_ != 1
                or list(m.classes_) != [0, 1]
                or not m.estimators_
            ):
                raise ValueError()
            detector = cls(m, version)
            detector._probability([0.0] * len(FEATURE_NAMES))
            return detector
        except Exception as e:
            raise ModelUnavailableError("학습된 분석 모델을 사용할 수 없습니다.") from e

    def _probability(self, vector):
        x = np.asarray(vector, dtype=float)
        if x.shape != (len(FEATURE_NAMES),) or not np.isfinite(x).all():
            raise ModelUnavailableError("특징 벡터 오류")
        p = np.asarray(self.model.predict_proba(x.reshape(1, -1)), dtype=float)
        if (
            p.shape != (1, 2)
            or not np.isfinite(p).all()
            or (p < 0).any()
            or (p > 1).any()
            or not np.isclose(p.sum(), 1)
        ):
            raise ModelUnavailableError("모델 출력 오류")
        return float(p[0, 1])

    def predict(self, url):
        normalized = normalize_url(url)
        try:
            score = max(
                0, min(100, round(self._probability(self.extractor.vector(normalized)) * 100))
            )
            reasons = []
            for r in self.extractor.explain(normalized):
                if not isinstance(r, str):
                    raise ValueError()
                r = " ".join(r.split())[:500]
                if r and r not in reasons:
                    reasons.append(r)
            return {
                "url": normalized,
                "status": "danger" if score >= 80 else "caution" if score >= 40 else "safe",
                "score": score,
                "reasons": reasons[:11] + ["관찰된 URL 특징이며 모델의 기여도 설명이 아닙니다."],
                "model_version": self.model_version,
            }
        except Exception as e:
            raise ModelUnavailableError("모델 예측에 실패했습니다.") from e
```

## server/linkguard/nlp.py

```python
"""Independently rebuilt bounded WDM/RWDM/MAM adaptations.

The small curated lexical data and all numeric cutoffs are experimental project
choices. They are not the paper's original dictionary, corpus or validated rules.
"""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re
from urllib.parse import unquote

RESOURCE_DIR = Path(__file__).with_name("resources")


def _words(name: str) -> frozenset[str]:
    return frozenset(
        line.strip().lower()
        for line in (RESOURCE_DIR / name).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


DICTIONARY = _words("dictionary.txt")
KEYWORDS = _words("keywords.txt")
BRAND_DOMAINS = {
    name: tuple(domains)
    for name, domains in json.loads((RESOURCE_DIR / "brands.json").read_text()).items()
}
BRANDS = frozenset(BRAND_DOMAINS)
OFFICIAL_DOMAINS = frozenset(domain for domains in BRAND_DOMAINS.values() for domain in domains)
KNOWN_TLDS = _words("known_tlds.txt")
LEXICON = DICTIONARY | KEYWORDS | BRANDS
_MAX_WORD_LENGTH = max(map(len, LEXICON))
_ALPHABET = "abcdefghijklmnopqrstuvwxyz "


def letters_only(word: str) -> str:
    return re.sub("[^a-z]", "", word.lower())


def raw_tokens(text: str) -> tuple[str, ...]:
    """Single percent decoding followed by ASCII alphanumeric tokenization."""
    return tuple(re.findall(r"[a-z0-9]+", unquote(text).lower()))


def decompose(word: str) -> tuple[str, ...]:
    """Non-overlap segmentation maximizing known coverage then longest words."""
    token = letters_only(word)
    if not token:
        return ()
    if token in LEXICON or len(token) <= 7 or len(token) > 80:
        return (token,)
    n = len(token)
    dp = [(0, 0, 0, ()) for _ in range(n + 1)]
    for start in range(n - 1, -1, -1):
        best = dp[start + 1]
        for end in range(start + 3, min(n, start + _MAX_WORD_LENGTH) + 1):
            if token[start:end] not in LEXICON:
                continue
            tail, length = dp[end], end - start
            candidate = (
                tail[0] + length,
                tail[1] + length * length,
                tail[2] - 1,
                ((start, end),) + tail[3],
            )
            if candidate[:3] > best[:3]:
                best = candidate
        dp[start] = best
    spans = dp[0][3]
    if len(spans) < 2:
        return (token,)
    result, previous = [], 0
    for start, end in spans:
        if start > previous:
            result.append(token[previous:start])
        result.append(token[start:end])
        previous = end
    if previous < n:
        result.append(token[previous:])
    return tuple(result)


def _learn_bigrams():
    text = (RESOURCE_DIR / "corpus.txt").read_text().lower() + " " + " ".join(sorted(LEXICON))
    pairs, totals = Counter(), Counter()
    for word in re.findall("[a-z]+", text):
        padded = " " + word + " "
        for a, b in zip(padded, padded[1:]):
            pairs[a, b] += 1
            totals[a] += 1
    return pairs, totals


_BIGRAMS, _TOTALS = _learn_bigrams()


def bigram_score(word: str) -> float:
    token = letters_only(word)
    if not token:
        return 0.0
    padded = " " + token + " "
    logs = [
        math.log((_BIGRAMS[a, b] + 0.2) / (_TOTALS[a] + 0.2 * len(_ALPHABET)))
        for a, b in zip(padded, padded[1:])
    ]
    return math.exp(sum(logs) / len(logs))


def is_random_word(word: str) -> bool:
    token = letters_only(word)
    if len(token) < 5 or token in LEXICON:
        return False
    parts = decompose(token)
    if len(parts) > 1 and all(part in LEXICON for part in parts):
        return False
    return bigram_score(token) < 0.025


def bounded_edit_distance(first: str, second: str, maximum: int = 1) -> int:
    if maximum < 0:
        raise ValueError("maximum must be nonnegative")
    if abs(len(first) - len(second)) > maximum:
        return maximum + 1
    if first == second:
        return 0
    if len(first) > len(second):
        first, second = second, first
    previous, sentinel = list(range(len(second) + 1)), maximum + 1
    for i, a in enumerate(first, 1):
        current = [sentinel] * (len(second) + 1)
        current[0] = i
        for j in range(max(1, i - maximum), min(len(second), i + maximum) + 1):
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != second[j - 1])
            )
        if min(current) > maximum:
            return sentinel
        previous = current
    return min(previous[-1], sentinel)


def similar_matches(word: str, targets: frozenset[str]) -> tuple[str, ...]:
    token = letters_only(word)
    if len(token) < 4 or len(token) > 64 or token in targets:
        return ()
    maximum = 2 if len(token) >= 8 else 1
    return tuple(
        target
        for target in sorted(targets)
        if len(target) >= 4 and bounded_edit_distance(token, target, maximum) <= maximum
    )
```

## server/linkguard/resources/brands.json

```json
{
  "google": ["google.com", "google.co.kr"],
  "gmail": ["gmail.com"],
  "microsoft": ["microsoft.com"],
  "outlook": ["outlook.com"],
  "office": ["office.com"],
  "apple": ["apple.com"],
  "icloud": ["icloud.com"],
  "amazon": ["amazon.com"],
  "paypal": ["paypal.com"],
  "facebook": ["facebook.com"],
  "instagram": ["instagram.com"],
  "github": ["github.com"],
  "dropbox": ["dropbox.com"],
  "netflix": ["netflix.com"],
  "naver": ["naver.com"],
  "kakao": ["kakao.com"],
  "daum": ["daum.net"],
  "coupang": ["coupang.com"],
  "samsung": ["samsung.com"],
  "shinhan": ["shinhan.com"],
  "woori": ["wooribank.com"],
  "kookmin": ["kbstar.com"],
  "hana": ["hanabank.com"],
  "nonghyup": ["nonghyup.com"],
  "koreapost": ["koreapost.go.kr"]
}
```

## server/linkguard/resources/corpus.txt

```text
This is a small curated local corpus for a reproducible experimental character pair model.
The user can inspect a website address before opening a link in a browser.
An account may receive a security notification about a password update.
The delivery service provides parcel tracking information and customer support.
The public library contains documents, guides and reference information.
The university publishes news, schedules and contact details on its website.
Check the sender and the domain before entering personal information.
Use the official application to review banking payments and account activity.
An online store sends an order confirmation and a shipping receipt.
The team manages a software project with source code and version history.
Words in this corpus do not define normal or phishing labels.
This corpus is not the training material used by the original research paper.
```

## server/linkguard/resources/dictionary.txt

```text
# Rebuilt curated English lexical inventory, not a comprehensive language model.
about
access
account
activity
address
admin
administrator
agent
alert
allow
app
apple
application
archive
authentication
available
balance
bank
banking
basic
billing
browser
business
calendar
camera
cancel
card
care
center
change
check
claim
client
cloud
code
company
computer
confirm
confirmation
connect
connection
contact
content
continue
control
copyright
create
credit
customer
data
date
default
delivery
department
detail
device
digital
directory
document
documentation
domain
download
email
example
exchange
file
financial
find
folder
form
free
general
global
government
group
guide
help
history
home
host
image
important
information
install
international
internet
invoice
item
language
learn
legal
library
link
list
live
local
location
login
logout
mail
main
manage
manager
market
member
message
mobile
money
name
network
news
normal
notice
notification
number
office
online
open
order
organization
page
parcel
password
pay
payment
pending
personal
phone
photo
platform
please
policy
portal
post
press
privacy
private
process
product
profile
project
protect
public
purchase
read
receipt
receive
recover
recovery
redirect
reference
refund
register
registration
release
remove
renew
report
request
reset
resource
response
restore
result
review
safe
safety
save
scan
schedule
search
secure
security
select
send
server
service
session
setting
setup
share
shipping
shop
shopping
sign
signin
signup
site
software
source
special
start
state
status
storage
store
student
subscribe
summary
support
system
team
technology
telephone
term
test
text
time
today
token
tool
tracking
transfer
travel
trusted
type
unlock
update
upgrade
upload
url
user
validate
validation
verification
verify
version
view
visit
warning
web
website
welcome
window
work
world
```

## server/linkguard/resources/keywords.txt

```text
account
activate
authentication
bank
billing
claim
confirm
delivery
invoice
login
parcel
password
payment
recover
refund
register
reset
secure
security
signin
support
tracking
unlock
update
verification
verify
wallet
```

## server/linkguard/resources/known_tlds.txt

```text
com
org
net
edu
gov
mil
int
io
co
kr
uk
de
fr
jp
au
ca
us
in
cn
info
biz
app
dev
```

## server/linkguard/training.py

```python
"""Rebuilt domain-disjoint training. Only trusted local artifacts may be loaded."""

from __future__ import annotations
import csv, hashlib, ipaddress, json, os, re, tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from .features import FeatureExtractor, FEATURE_NAMES, FEATURE_SCHEMA_VERSION, RESOURCE_FINGERPRINT
from .urltools import normalize_url, domain_group

THRESHOLDS = {"caution": 40, "danger": 80}
VERSION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z")


class TrainingDataError(ValueError):
    pass


@dataclass(frozen=True)
class Dataset:
    urls: tuple[str, ...]
    labels: tuple[int, ...]
    groups: tuple[str, ...]
    canonical_keys: tuple[str, ...]
    raw_count: int
    duplicate_count: int
    data_sha256: str


@dataclass(frozen=True)
class DatasetSplit:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


def canonical_dataset_url(url):
    p = urlsplit(normalize_url(url))
    host = p.hostname
    try:
        host = ipaddress.ip_address(host).compressed
    except ValueError:
        pass
    if ":" in host:
        host = "[" + host + "]"
    if p.port and (p.scheme, p.port) not in [("https", 443), ("http", 80)]:
        host += ":" + str(p.port)
    return urlunsplit((p.scheme, host, p.path or "/", p.query, ""))


def load_dataset(csv_path):
    try:
        with Path(csv_path).open("rb") as f:
            payload = f.read(200 * 1024 * 1024 + 1)
        if len(payload) > 200 * 1024 * 1024:
            raise TrainingDataError("CSV는 200 MiB 이하여야 합니다.")
        text = payload.decode("utf-8-sig")
    except (OSError, UnicodeError) as e:
        raise TrainingDataError("UTF-8 CSV 파일을 읽을 수 없습니다.") from e
    import io

    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if (
        not reader.fieldnames
        or len(set(reader.fieldnames)) != len(reader.fieldnames)
        or not {"url", "label"} <= set(reader.fieldnames)
    ):
        raise TrainingDataError("CSV에 url,label 열이 필요합니다.")
    urls = []
    labels = []
    groups = []
    keys = []
    seen = {}
    raw = duplicate = 0
    try:
        for row in reader:
            raw += 1
            number = reader.line_num
            if (
                None in row
                or row.get("url") is None
                or row.get("label") is None
                or row["label"].strip() not in ("0", "1")
            ):
                raise TrainingDataError(f"CSV {number}행의 열과 라벨을 확인하세요.")
            label = int(row["label"].strip())
            try:
                normalized = normalize_url(row["url"].strip())
                key = canonical_dataset_url(normalized)
                group = domain_group(normalized)
            except Exception:
                raise TrainingDataError(f"CSV {number}행의 URL 형식을 확인하세요.") from None
            if key in seen:
                if seen[key] != label:
                    raise TrainingDataError(f"CSV {number}행의 중복 URL 라벨이 충돌합니다.")
                duplicate += 1
                continue
            seen[key] = label
            urls.append(normalized)
            labels.append(label)
            groups.append(group)
            keys.append(key)
    except csv.Error:
        raise TrainingDataError("CSV 형식이 올바르지 않습니다.") from None
    if not urls:
        raise TrainingDataError("CSV가 비어 있습니다.")
    return Dataset(
        tuple(urls),
        tuple(labels),
        tuple(groups),
        tuple(keys),
        raw,
        duplicate,
        hashlib.sha256(payload).hexdigest(),
    )


def _valid(y, n=2):
    return all(np.sum(y == label) >= n for label in (0, 1))


def split_dataset(dataset, test_size=0.2, seed=42):
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**32:
        raise TrainingDataError("seed 범위 오류")
    if (
        not isinstance(test_size, (float, int))
        or not np.isfinite(test_size)
        or not 0.1 <= test_size <= 0.5
    ):
        raise TrainingDataError("test-size 범위는 0.1~0.5입니다.")
    y = np.array(dataset.labels)
    g = np.array(dataset.groups)
    if len(y) < 20 or not _valid(y, 5) or any(len(set(g[y == v])) < 4 for v in (0, 1)):
        raise TrainingDataError("최소 20개 URL, 라벨별 5개 URL과 4개 독립 도메인이 필요합니다.")
    for train, test in GroupShuffleSplit(
        n_splits=128, test_size=test_size, random_state=seed
    ).split(y, y, g):
        if (
            _valid(y[train])
            and _valid(y[test])
            and all(len(set(g[train][y[train] == v])) >= 2 for v in (0, 1))
        ):
            assert not set(g[train]) & set(g[test])
            return DatasetSplit(tuple(map(int, train)), tuple(map(int, test)))
    raise TrainingDataError("두 라벨을 포함하는 독립 도메인 분할이 불가능합니다.")


def _metrics(y, p):
    tn, fp, fn, tp = map(int, confusion_matrix(y, p, labels=[0, 1]).ravel())
    return dict(
        accuracy=float(accuracy_score(y, p)),
        precision=float(precision_score(y, p, zero_division=0)),
        recall=float(recall_score(y, p, zero_division=0)),
        f1=float(f1_score(y, p, zero_division=0)),
        false_positive_rate=fp / (fp + tn),
        confusion_matrix=dict(tn=tn, fp=fp, fn=fn, tp=tp),
    )


def _atomic(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name)
    os.close(fd)
    try:
        writer(tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def train_model(
    csv_path,
    output_path="artifacts/linkguard.joblib",
    report_path="artifacts/metrics.json",
    *,
    cv_folds=0,
    seed=42,
    test_size=0.2,
    trees=200,
    model_version=None,
):
    if len({Path(p).resolve() for p in [csv_path, output_path, report_path]}) != 3:
        raise TrainingDataError("입력과 출력 경로는 달라야 합니다.")
    if type(trees) != int or not 10 <= trees <= 2000:
        raise TrainingDataError("trees는 10~2000 정수여야 합니다.")
    if type(cv_folds) != int or cv_folds not in [0, *range(2, 11)]:
        raise TrainingDataError("CV는 0 또는 2~10이어야 합니다.")
    if model_version is not None and (
        not isinstance(model_version, str) or not VERSION_PATTERN.fullmatch(model_version)
    ):
        raise TrainingDataError(
            "모델 버전은 영숫자로 시작하는 최대 120자 영숫자/._- 문자열이어야 합니다."
        )
    d = load_dataset(csv_path)
    s = split_dataset(d, test_size, seed)
    e = FeatureExtractor()
    x = np.array([e.vector(u) for u in d.urls], dtype=float)
    y = np.array(d.labels)
    g = np.array(d.groups)
    train = np.array(s.train_indices)
    test = np.array(s.test_indices)
    if x.shape != (len(y), len(FEATURE_NAMES)) or not np.isfinite(x).all():
        raise TrainingDataError("특징 벡터 오류")
    model = RandomForestClassifier(
        n_estimators=trees, random_state=seed, class_weight="balanced", n_jobs=2
    )
    cv = None
    if cv_folds:
        if any(len(set(g[train][y[train] == v])) < cv_folds for v in (0, 1)):
            raise TrainingDataError("CV에 필요한 독립 도메인이 부족합니다.")
        folds = list(
            StratifiedGroupKFold(cv_folds, shuffle=True, random_state=seed).split(
                x[train], y[train], g[train]
            )
        )
        if any(not _valid(y[train][a]) or not _valid(y[train][b]) for a, b in folds):
            raise TrainingDataError("CV 각 구간에 두 라벨이 충분히 필요합니다.")
        results = []
        for a, b in folds:
            assert not set(g[train][a]) & set(g[train][b])
            candidate = clone(model).fit(x[train][a], y[train][a])
            results.append(_metrics(y[train][b], candidate.predict(x[train][b])))
        cv = {"scope": "training_partition_only", "fold_count": cv_folds, "folds": results}
    model.fit(x[train], y[train])
    version = (
        model_version
        or f"rf-rebuilt-{d.data_sha256[:8]}-s{seed}-t{trees}-{RESOURCE_FINGERPRINT[:8]}"
    )
    group_hashes = lambda values: sorted(
        hashlib.sha256(v.encode()).hexdigest() for v in set(values)
    )
    scores = np.rint(model.predict_proba(x[test])[:, 1] * 100).astype(int)
    report = {
        "model_version": version,
        "algorithm": "RandomForestClassifier",
        "sklearn_version": sklearn.__version__,
        "feature_names": list(FEATURE_NAMES),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "resource_fingerprint": RESOURCE_FINGERPRINT,
        "training": {"trees": trees, "seed": seed, "refit_on_holdout": False},
        "dataset": {
            "unique_urls": len(y),
            "input_rows": d.raw_count,
            "duplicate_rows_removed": d.duplicate_count,
            "data_sha256": d.data_sha256,
        },
        "split": {
            "method": "registrable_domain_group_holdout",
            "seed": seed,
            "train_samples": len(train),
            "test_samples": len(test),
            "overlapping_groups": 0,
            "holdout_used_for_fit": False,
            "train_group_hashes": group_hashes(g[train]),
            "test_group_hashes": group_hashes(g[test]),
        },
        "holdout": _metrics(y[test], model.predict(x[test])),
        "cross_validation": cv,
        "warning_policy_holdout": {
            str(t): _metrics(y[test], (scores >= t).astype(int)) for t in (40, 80)
        },
        "limitations": [
            "합성 데이터 지표는 실제 성능이 아닙니다.",
            "40/80 경계와 RF 점수는 보정되지 않은 시제품 신호입니다.",
            "도메인 분리만으로 모든 캠페인/시간 누수를 제거할 수 없습니다.",
        ],
    }
    artifact = {
        "artifact_version": 1,
        "feature_names": list(FEATURE_NAMES),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "resource_fingerprint": RESOURCE_FINGERPRINT,
        "model_version": version,
        "model": model,
        "thresholds": THRESHOLDS,
        "metadata": {
            "sklearn_version": sklearn.__version__,
            "data_sha256": d.data_sha256,
            "holdout_used_for_fit": False,
            "training_sample_count": len(train),
            "seed": seed,
            "trees": trees,
        },
    }
    _atomic(output_path, lambda p: joblib.dump(artifact, p, compress=3))
    _atomic(
        report_path,
        lambda p: Path(p).write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
        ),
    )
    return report
```

## server/linkguard/urltools.py

```python
"""Rebuilt HTTP(S) parser and offline registrable-domain grouping.

This module never resolves DNS, opens the inspected URL or downloads a suffix list.
The normalization examples and UTF-16 length limit match the Kotlin client contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import ipaddress
import re
from urllib.parse import urlsplit

import tldextract

MAX_URL_LENGTH = 4096
_HTTP = re.compile(r"^https?://", re.I)
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
_HOST_PORT = re.compile(r"^[^/:?#]+\.[^/:?#]+:[0-9]+(?:[/?#]|$)")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_BAD_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
_SUFFIXES = tldextract.TLDExtract(
    cache_dir=None, suffix_list_urls=(), include_psl_private_domains=True
)


class URLValidationError(ValueError):
    """The input is not an accepted HTTP(S) URL."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise URLValidationError(message)


def _utf16_units(value: str) -> int:
    try:
        return len(value.encode("utf-16-le")) // 2
    except UnicodeEncodeError:
        raise URLValidationError("Unpaired Unicode surrogate is not permitted") from None


def _authority(value: str) -> tuple[str, str, bool]:
    _require(bool(value) and "@" not in value, "Missing host or credentials are not supported")
    if value.startswith("["):
        end = value.find("]")
        _require(end > 1, "Malformed IPv6 literal")
        host, port = value[1:end], value[end + 1 :]
        _require(
            bool(re.fullmatch(r"[0-9a-fA-F:.]+", host)) and ":" in host, "Malformed IPv6 literal"
        )
        try:
            ipaddress.IPv6Address(host)
        except ValueError:
            raise URLValidationError("Malformed IPv6 literal") from None
        host, ipv6 = host.lower(), True
    else:
        _require(value.count(":") <= 1, "IPv6 addresses require square brackets")
        host, sep, tail = value.rpartition(":")
        if not sep:
            host, port = value, ""
        else:
            port = ":" + tail
        try:
            host = host.encode("idna").decode("ascii").lower().removesuffix(".")
        except (UnicodeError, ValueError):
            raise URLValidationError("Malformed domain") from None
        labels = host.split(".")
        _require(
            len(host) <= 253 and len(labels) >= 2 and all(_LABEL.fullmatch(x) for x in labels),
            "Malformed domain",
        )
        if re.fullmatch(r"[0-9.]+", host):
            try:
                ipaddress.IPv4Address(host)
            except ValueError:
                raise URLValidationError("Malformed IPv4 literal") from None
        ipv6 = False
    _require(
        not port or bool(re.fullmatch(r":[0-9]{1,5}", port)) and 1 <= int(port[1:]) <= 65535,
        "Port must be between 1 and 65535",
    )
    return host, port, ipv6


def normalize_url(value: str) -> str:
    """Default to HTTPS, normalize host, and preserve path/query/fragment spelling."""
    _require(isinstance(value, str), "URL must be a string")
    _require(_utf16_units(value) <= MAX_URL_LENGTH, "URL exceeds 4096 UTF-16 units")
    _require(
        not any(ord(x) < 32 or ord(x) == 127 for x in value), "Control characters are not permitted"
    )
    text = value.strip()
    _require(bool(text), "URL is empty")
    _require(
        not any(x.isspace() or x == "\\" for x in text),
        "Whitespace or backslashes are not permitted",
    )
    _require(not any(x in '<>"{}|^`' for x in text), "Invalid URI character")
    _require(not _BAD_PERCENT.search(text), "Malformed percent escape")
    explicit = bool(_HTTP.match(text))
    _require(
        not text.startswith("//")
        and (
            explicit
            or not _SCHEME.match(text)
            or bool(_HOST_PORT.match(text))
            or text.startswith("[")
        ),
        "Only HTTP(S) URLs are supported",
    )
    candidate = text if explicit else "https://" + text
    try:
        parts = urlsplit(candidate)
    except (ValueError, UnicodeError):
        raise URLValidationError("Malformed URL") from None
    _require(parts.scheme.lower() in ("http", "https"), "Only HTTP(S) URLs are supported")
    host, port, ipv6 = _authority(parts.netloc)
    _require(not parts.path or parts.path.startswith("/"), "Malformed path")
    _require(
        "[" not in parts.path and "]" not in parts.path and "#" not in parts.fragment,
        "Malformed path or fragment",
    )
    prefix, fragment_sep, _ = candidate.partition("#")
    result = parts.scheme.lower() + "://" + ("[" + host + "]" if ipv6 else host) + port + parts.path
    if "?" in prefix:
        result += "?" + parts.query
    if fragment_sep:
        result += "#" + parts.fragment
    _require(_utf16_units(result) <= MAX_URL_LENGTH, "Normalized URL exceeds 4096 UTF-16 units")
    return result


@dataclass(frozen=True)
class ParsedURL:
    normalized: str
    hostname: str
    registered_domain: str
    domain_label: str
    suffix: str
    subdomain: str
    path_query: str
    is_ip: bool


@lru_cache(maxsize=8192)
def _domain_parts(host: str) -> tuple[str, str, str, str, bool]:
    try:
        canonical = str(ipaddress.ip_address(host))
    except ValueError:
        pass
    else:
        return canonical, host, "", "", True
    result = _SUFFIXES(host)
    labels = host.split(".")
    if result.suffix and result.domain:
        return (
            result.domain + "." + result.suffix,
            result.domain,
            result.suffix,
            result.subdomain,
            False,
        )
    if result.suffix:
        return host, labels[0], result.suffix, "", False
    return ".".join(labels[-2:]), labels[-2], labels[-1], ".".join(labels[:-2]), False


def parse_url(value: str) -> ParsedURL:
    normalized = normalize_url(value)
    parts = urlsplit(normalized)
    host = (
        parts.netloc[1 : parts.netloc.index("]")]
        if parts.netloc.startswith("[")
        else parts.netloc.split(":", 1)[0]
    )
    registered, label, suffix, subdomain, is_ip = _domain_parts(host)
    path_query = parts.path + ("?" + parts.query if "?" in normalized.partition("#")[0] else "")
    return ParsedURL(normalized, host, registered, label, suffix, subdomain, path_query, is_ip)


def domain_group(value: str) -> str:
    """Offline registered-domain group used to prevent domain overlap at evaluation."""
    return parse_url(value).registered_domain
```

## server/requirements-dev.txt

```text
-r requirements.txt
httpx==0.28.1
```

## server/requirements-lock.txt

```text
annotated-doc==0.0.6
annotated-types==0.8.0
anyio==4.16.0
certifi==2026.10.23
charset-normalizer==3.5.2
click==8.5.1
fastapi==0.141.1
filelock==4.2.12
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.20
joblib==1.5.3
numpy==2.3.5
pydantic==2.14.3
pydantic_core==2.50.4
requests==2.34.2
requests-file==3.0.1
scikit-learn==1.8.0
scipy==1.18.1
starlette==1.10.0
threadpoolctl==3.8.0
tldextract==5.3.0
typing-inspection==0.4.5
typing_extensions==4.16.0
urllib3==2.8.0
uvicorn==0.52.1
```

## server/requirements.txt

```text
fastapi==0.141.1
uvicorn==0.52.1
scikit-learn==1.8.0
numpy==2.3.5
joblib==1.5.3
tldextract==5.3.0
```

## server/server.py

```python
"""Rebuilt LinkGuard API; no scanned URL fetching or request-body logging."""

import asyncio, os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from starlette.concurrency import run_in_threadpool
from linkguard.features import FEATURE_SCHEMA_VERSION
from linkguard.urltools import normalize_url, URLValidationError
from linkguard.model import URLDetector, ModelUnavailableError


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                try:
                    length = int(value)
                    if length < 0:
                        raise ValueError()
                except ValueError:
                    return await JSONResponse(
                        {"detail": "요청 형식이 올바르지 않습니다."}, status_code=400
                    )(scope, receive, send)
                if length > 16384:
                    return await JSONResponse(
                        {"detail": "요청 본문이 너무 큽니다."}, status_code=413
                    )(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > 16384:
                return await JSONResponse({"detail": "요청 본문이 너무 큽니다."}, status_code=413)(
                    scope, receive, send
                )
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: StrictStr = Field(min_length=1, max_length=4096)


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str
    status: Literal["safe", "caution", "danger"]
    score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(min_length=1, max_length=12)
    model_version: str = Field(min_length=1, max_length=120)


def create_app(model_path=None):
    path = (
        model_path
        if model_path is not None
        else os.getenv(
            "LINKGUARD_MODEL_PATH",
            str(Path(__file__).resolve().parent / "artifacts/linkguard.joblib"),
        )
    )

    @asynccontextmanager
    async def lifespan(app):
        app.state.gate = asyncio.Semaphore(4)
        try:
            app.state.detector = await run_in_threadpool(URLDetector.load, path)
        except ModelUnavailableError:
            app.state.detector = None
        yield
        app.state.detector = None

    app = FastAPI(title="LinkGuard Rebuilt", lifespan=lifespan)
    app.state.detector = None
    app.add_middleware(BodyLimit)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse({"detail": "URL 입력 형식이 올바르지 않습니다."}, status_code=422)

    @app.get("/health")
    async def health():
        return {
            "status": "ready" if app.state.detector else "model_unavailable",
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
        }

    @app.post("/predict", response_model=Prediction)
    async def predict(request: Request):
        try:
            url = normalize_url(request.url)
        except (URLValidationError, ValueError):
            raise HTTPException(422, "URL 입력 형식이 올바르지 않습니다.") from None
        if app.state.detector is None:
            raise HTTPException(503, "학습된 분석 모델이 준비되지 않았습니다.")
        gate = app.state.gate
        if gate.locked():
            raise HTTPException(503, "분석 요청이 많습니다.")
        await gate.acquire()
        try:
            return await run_in_threadpool(app.state.detector.predict, url)
        except Exception:
            app.state.detector = None
            raise HTTPException(503, "분석 모델을 사용할 수 없습니다.") from None
        finally:
            gate.release()

    return app


app = create_app()
```

## server/tests/test_api.py

```python
import unittest, tempfile, socket
from pathlib import Path
from unittest.mock import patch
import joblib, numpy as np, sklearn
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
from linkguard.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    RESOURCE_FINGERPRINT,
    FeatureExtractor,
)
from linkguard.model import URLDetector, ModelUnavailableError
from server import create_app


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "model.joblib"
        x = np.array(
            [
                FeatureExtractor().vector(u)
                for u in [
                    "https://docs.example/help",
                    "https://guide.example",
                    "http://parcel-verify.example/login",
                    "http://192.0.2.1/verify",
                ]
            ]
        )
        m = RandomForestClassifier(n_estimators=10, random_state=1).fit(x, [0, 0, 1, 1])
        self.artifact = {
            "artifact_version": 1,
            "feature_names": list(FEATURE_NAMES),
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "resource_fingerprint": RESOURCE_FINGERPRINT,
            "model_version": "synthetic-test-only",
            "model": m,
            "thresholds": {"caution": 40, "danger": 80},
            "metadata": {"sklearn_version": sklearn.__version__},
        }
        joblib.dump(self.artifact, self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_prediction_contract(self):
        with TestClient(create_app(self.path)) as c:
            self.assertEqual(c.get("/health").json()["status"], "ready")
            r = c.post("/predict", json={"url": "HTTPS://Example.com/a?x=1#f"})
            self.assertEqual(r.status_code, 200)
            j = r.json()
            self.assertEqual(j["url"], "https://example.com/a?x=1#f")
            self.assertIs(type(j["score"]), int)
            self.assertTrue(0 <= j["score"] <= 100)
            self.assertTrue(1 <= len(j["reasons"]) <= 12)
            self.assertEqual(set(j), {"url", "status", "score", "reasons", "model_version"})

    def test_missing_model_503_no_fake_score(self):
        with TestClient(create_app(self.path.parent / "missing")) as c:
            self.assertEqual(c.get("/health").json()["status"], "model_unavailable")
            r = c.post("/predict", json={"url": "https://example.com"})
            self.assertEqual(r.status_code, 503)
            self.assertNotIn("score", r.json())

    def test_invalid_inputs_generic_422(self):
        with TestClient(create_app(self.path)) as c:
            for body in [
                {"url": "javascript:alert(1)"},
                {"url": 4},
                {"url": True},
                {"url": "https://example.com", "extra": 1},
                {},
            ]:
                r = c.post("/predict", json=body)
                self.assertEqual(r.status_code, 422)
                self.assertNotIn("javascript", r.text)

    def test_oversize_and_no_cors(self):
        with TestClient(create_app(self.path)) as c:
            self.assertEqual(c.post("/predict", content=b"a" * 16385).status_code, 413)
            self.assertNotIn(
                "access-control-allow-origin",
                c.get("/health", headers={"Origin": "https://other.example"}).headers,
            )

    def test_incompatible_artifacts_fail_closed(self):
        for key, value in [
            ("feature_names", []),
            ("resource_fingerprint", "wrong"),
            ("model_version", "bad\nversion"),
            ("thresholds", {}),
        ]:
            bad = dict(self.artifact)
            bad[key] = value
            joblib.dump(bad, self.path)
            with self.assertRaises(ModelUnavailableError):
                URLDetector.load(self.path)

    def test_corrupt_artifact(self):
        self.path.write_bytes(b"not a model")
        with self.assertRaises(ModelUnavailableError):
            URLDetector.load(self.path)

    def test_prediction_never_resolves_url(self):
        d = URLDetector.load(self.path)
        with patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")
        ), patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ):
            self.assertIn("score", d.predict("https://safe.example/a"))

    def test_bad_prediction_disables_model_generic_503(self):
        with TestClient(create_app(self.path)) as c:
            with patch.object(
                c.app.state.detector, "predict", side_effect=RuntimeError("private-url-token")
            ):
                r = c.post("/predict", json={"url": "https://example.com"})
                self.assertEqual(r.status_code, 503)
                self.assertNotIn("private", r.text)

    def test_busy_gate_returns_503(self):
        import asyncio

        with TestClient(create_app(self.path)) as c:
            c.app.state.gate = asyncio.Semaphore(0)
            self.assertEqual(
                c.post("/predict", json={"url": "https://example.com"}).status_code, 503
            )

    def test_chunked_asgi_body_limit_prevents_app_call(self):
        import asyncio
        from server import BodyLimit

        sent = []
        chunks = iter(
            [
                {"type": "http.request", "body": b"a" * 10000, "more_body": True},
                {"type": "http.request", "body": b"b" * 7000, "more_body": False},
            ]
        )

        async def downstream(scope, receive, send):
            raise AssertionError("oversize body reached parser")

        async def receive():
            return next(chunks)

        async def send(message):
            sent.append(message)

        asyncio.run(BodyLimit(downstream)({"type": "http"}, receive, send))
        self.assertEqual(sent[0]["status"], 413)

    def test_content_length_rejected_without_reading_body(self):
        import asyncio
        from server import BodyLimit

        for header, status in [(b"16385", 413), (b"-1", 400), (b"bad", 400)]:
            with self.subTest(header=header):
                sent = []

                async def downstream(scope, receive, send):
                    raise AssertionError("rejected request reached app")

                async def receive():
                    raise AssertionError("rejected header triggered body read")

                async def send(message):
                    sent.append(message)

                asyncio.run(
                    BodyLimit(downstream)(
                        {"type": "http", "headers": [(b"content-length", header)]}, receive, send
                    )
                )
                self.assertEqual(sent[0]["status"], status)
```

## server/tests/test_features.py

```python
"""Behavior checks for rebuilt lexical features; not an accuracy benchmark."""

import math
import socket
import unittest
from unittest.mock import patch

from linkguard.features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    RESOURCE_FINGERPRINT,
    FeatureExtractor,
)
from linkguard.nlp import (
    BRANDS,
    KEYWORDS,
    bigram_score,
    bounded_edit_distance,
    decompose,
    is_random_word,
    raw_tokens,
    similar_matches,
)


class NLPTests(unittest.TestCase):
    def test_wdm_preserves_known_words_and_uncovered_spans(self):
        self.assertEqual(decompose("secure1login"), ("secure", "login"))
        self.assertEqual(decompose("paypalverify"), ("paypal", "verify"))
        self.assertEqual(decompose("xsecurelogin"), ("x", "secure", "login"))
        self.assertEqual(decompose("authentication"), ("authentication",))
        self.assertEqual(decompose("secure"), ("secure",))
        self.assertEqual(decompose("123"), ())
        self.assertEqual(decompose("q" * 81), ("q" * 81,))

    def test_random_word_model_is_smoothed_bounded_and_experimental(self):
        self.assertGreater(bigram_score("delivery"), bigram_score("xqzvjkbn"))
        self.assertTrue(is_random_word("xqzvjkbn"))
        self.assertFalse(is_random_word("delivery"))
        self.assertFalse(is_random_word("securelogin"))
        self.assertFalse(is_random_word("qzx"))
        self.assertEqual(bigram_score("123"), 0)
        self.assertTrue(math.isfinite(bigram_score("z" * 4096)))

    def test_mam_edit_distance_excludes_exact_matches(self):
        self.assertEqual(bounded_edit_distance("goggle", "google"), 1)
        self.assertEqual(bounded_edit_distance("login", "login", 0), 0)
        self.assertEqual(bounded_edit_distance("kitten", "sitting", 2), 3)
        self.assertIn("google", similar_matches("goggle", BRANDS))
        self.assertIn("login", similar_matches("logim", KEYWORDS))
        self.assertEqual(similar_matches("google", BRANDS), ())
        self.assertEqual(similar_matches("x" * 65, BRANDS), ())

    def test_tokenizer_decodes_once(self):
        self.assertEqual(raw_tokens("secure%6Cogin/a12?x=9"), ("securelogin", "a12", "x", "9"))
        self.assertEqual(raw_tokens("%2520"), ("20",))


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()

    def test_schema_exactly_forty_and_stable_finite_order(self):
        self.assertEqual(len(FEATURE_NAMES), 40)
        self.assertEqual(len(set(FEATURE_NAMES)), 40)
        self.assertEqual(FEATURE_NAMES[-2:], ("uses_https", "host_is_ip"))
        self.assertEqual(FEATURE_SCHEMA_VERSION, "sahingoz-adapted-v1-rebuilt")
        self.assertRegex(RESOURCE_FINGERPRINT, "^[0-9a-f]{64}$")
        result = self.extractor.extract("https://example.com")
        self.assertEqual(tuple(result), FEATURE_NAMES)
        self.assertEqual(self.extractor.vector("https://example.com"), list(result.values()))
        self.assertTrue(all(type(x) is float and math.isfinite(x) for x in result.values()))

    def test_simple_raw_word_statistics_are_inspectable(self):
        x = self.extractor.extract("https://example.com")
        for key, expected in [
            ("raw_word_count", 2),
            ("average_word_length", 5),
            ("longest_word_length", 7),
            ("shortest_word_length", 3),
            ("word_length_std", 2),
            ("length_domain", 7),
            ("known_tld", 1),
            ("count_slash", 2),
            ("uses_https", 1),
            ("host_is_ip", 0),
        ]:
            self.assertEqual(x[key], expected)

    def test_compound_keyword_and_typo_features(self):
        x = self.extractor.extract("http://secure1login.example/verify")
        self.assertEqual(x["adjacent_word_count"], 1)
        self.assertEqual(x["average_adjacent_word_length"], 11)
        self.assertEqual(x["separated_word_count"], 2)
        self.assertEqual(x["keyword_count"], 3)
        self.assertEqual(x["target_keyword_count"], 2)
        self.assertEqual(
            self.extractor.extract("https://goggle.com")["similar_brand_name_count"], 1
        )

    def test_random_words_removed_before_mam(self):
        self.assertTrue(is_random_word("kqkao"))
        self.assertIn("kakao", similar_matches("kqkao", BRANDS))
        x = self.extractor.extract("https://kqkao.example")
        self.assertEqual(x["random_word_count"], 1)
        self.assertEqual(x["similar_brand_name_count"], 0)
        self.assertEqual(x["random_domain"], 1)

    def test_brand_membership_not_ownership_and_target_scope(self):
        official = self.extractor.extract("https://www.google.com")
        self.assertEqual(official["brand_check_domain"], 1)
        self.assertEqual(official["target_brand_name_count"], 1)
        fake = self.extractor.extract("https://google.example")
        self.assertEqual(fake["brand_check_domain"], 0)
        self.assertEqual(fake["target_brand_name_count"], 1)
        sub = self.extractor.extract("https://google.other.example")
        self.assertEqual(sub["brand_name_count"], 1)
        self.assertEqual(sub["target_brand_name_count"], 0)
        self.assertEqual(self.extractor.extract("https://naver.com")["brand_check_domain"], 1)

    def test_component_digits_lengths_and_full_url_symbols(self):
        tail = "/p34?q=5&v_6=7"
        x = self.extractor.extract("https://s1.s2.a12.example.com" + tail + "#f8")
        self.assertEqual(x["digit_count_domain"], 0)
        self.assertEqual(x["digit_count_subdomain"], 4)
        self.assertEqual(x["digit_count_path"], 5)
        self.assertEqual(x["subdomain_count"], 3)
        self.assertEqual(x["length_path"], len(tail))
        self.assertEqual(x["count_question"], 1)
        self.assertEqual(x["count_equal"], 2)
        special = self.extractor.extract("https://www.com.example.com/a-aa/@x")
        self.assertEqual(special["www_in_domain_subdomain"], 1)
        self.assertEqual(special["com_in_domain_subdomain"], 1)
        self.assertEqual(special["count_hyphen"], 1)
        self.assertEqual(special["count_at"], 1)
        self.assertEqual(special["consecutive_character_repeat"], 4)

    def test_idn_ip_ipv6_private_suffix_inputs(self):
        for url, puny, ip in [
            ("https://bücher.de", 1, 0),
            ("http://192.0.2.10/verify", 0, 1),
            ("https://[2001:db8::1]/", 0, 1),
            ("https://team.github.io/", 0, 0),
        ]:
            with self.subTest(url=url):
                x = self.extractor.extract(url)
                self.assertEqual(x["punycode"], puny)
                self.assertEqual(x["host_is_ip"], ip)
                self.assertTrue(all(math.isfinite(v) for v in x.values()))
        self.assertEqual(self.extractor.extract("https://team.github.io")["length_domain"], 4)
        self.assertEqual(self.extractor.extract("https://www.example.co.uk")["length_domain"], 7)

    def test_explanations_are_factual_limited_observations(self):
        reasons = self.extractor.explain(
            "http://a1.b2.xn--naver-verify.example/goggle/login?" + "q" * 100
        )
        self.assertTrue(1 <= len(reasons) <= 12)
        self.assertTrue(all(0 < len(x.encode("utf-16-le")) // 2 <= 500 for x in reasons))
        self.assertTrue(any("HTTP" in x for x in reasons))
        self.assertFalse(any("97.98" in x or "안전합니다" in x for x in reasons))

    def test_feature_extraction_makes_no_dns_or_network_connections(self):
        with patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("No DNS")
        ), patch.object(socket, "create_connection", side_effect=AssertionError("No connection")):
            self.assertEqual(
                len(self.extractor.vector("https://a.brand.project.github.io/p?q=1")), 40
            )

    def test_maximum_length_token_remains_finite(self):
        prefix = "https://example.com/"
        vector = self.extractor.vector(prefix + "q" * (4096 - len(prefix)))
        self.assertEqual(len(vector), 40)
        self.assertTrue(all(math.isfinite(x) for x in vector))


if __name__ == "__main__":
    unittest.main()
```

## server/tests/test_training.py

```python
import unittest, tempfile, csv, json
from pathlib import Path
import joblib
from linkguard.training import (
    load_dataset,
    split_dataset,
    train_model,
    TrainingDataError,
    canonical_dataset_url,
)
from linkguard.model import URLDetector


class TrainingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def csv(self, rows):
        p = self.root / "urls.csv"
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["url", "label"])
            w.writerows(rows)
        return p

    def rows(self):
        return [
            (
                f'{"https" if y==0 else "http"}://{"docs" if y==0 else "parcel-verify"}{i}.example/{path}',
                y,
            )
            for y in (0, 1)
            for i in range(12)
            for path in ["help", "login"]
        ]

    def test_group_split_disjoint_and_repeatable(self):
        d = load_dataset(self.csv(self.rows()))
        s = split_dataset(d)
        self.assertEqual(s, split_dataset(d))
        self.assertFalse(
            {d.groups[i] for i in s.train_indices} & {d.groups[i] for i in s.test_indices}
        )

    def test_duplicate_key_keeps_normalized_representative(self):
        d = load_dataset(
            self.csv([("https://EXAMPLE.com:443#one", 0), ("https://example.com/#two", 0)])
        )
        self.assertEqual(d.duplicate_count, 1)
        self.assertEqual(d.urls[0], "https://example.com:443#one")

    def test_conflicting_labels_no_raw_url(self):
        with self.assertRaises(TrainingDataError) as c:
            load_dataset(
                self.csv([("https://private.example", 0), ("https://private.example:443/", 1)])
            )
        self.assertNotIn("private", str(c.exception))

    def test_ipv6_alias_key(self):
        self.assertEqual(
            canonical_dataset_url("https://[2001:0db8::1]:443#x"),
            canonical_dataset_url("https://[2001:db8::1]/"),
        )

    def test_tiny_dataset_rejected(self):
        with self.assertRaises(TrainingDataError):
            split_dataset(
                load_dataset(self.csv([("https://a.example", 0), ("https://b.example", 1)]))
            )

    def test_invalid_input_rejected(self):
        for row in [("javascript:alert(1)", 0), ("https://example.com", 2)]:
            with self.assertRaises(TrainingDataError):
                load_dataset(self.csv([row]))

    def test_train_cv_artifact_and_report(self):
        out = self.root / "m.joblib"
        rep = self.root / "r.json"
        r = train_model(self.csv(self.rows()), out, rep, trees=10, cv_folds=2)
        self.assertFalse(r["split"]["holdout_used_for_fit"])
        self.assertEqual(r["split"]["overlapping_groups"], 0)
        self.assertEqual(r["cross_validation"]["scope"], "training_partition_only")
        self.assertEqual(set(r["warning_policy_holdout"]), {"40", "80"})
        a = joblib.load(out)
        self.assertEqual(a["metadata"]["training_sample_count"], r["split"]["train_samples"])
        self.assertEqual(
            URLDetector.load(out).predict("https://example.com")["model_version"],
            r["model_version"],
        )
        self.assertEqual(json.loads(rep.read_text())["model_version"], r["model_version"])

    def test_bad_options_and_same_paths(self):
        p = self.csv(self.rows())
        for kwargs in [
            {"trees": 1},
            {"model_version": "bad\nversion"},
            {"model_version": "한글"},
            {"cv_folds": 1},
        ]:
            with self.assertRaises(TrainingDataError):
                train_model(p, self.root / "m", self.root / "r", **kwargs)
        with self.assertRaises(TrainingDataError):
            train_model(p, p, self.root / "r")
```

## server/tests/test_urltools.py

```python
"""Read-only normalization, Kotlin-contract and offline PSL behavior checks."""

import socket
import unittest
from unittest.mock import patch

from linkguard.urltools import URLValidationError, domain_group, normalize_url, parse_url


class URLToolsTests(unittest.TestCase):
    def test_normalization_preserves_application_components(self):
        cases = {
            " EXAMPLE.com/Path?q=A%2FB#frag ": "https://example.com/Path?q=A%2FB#frag",
            "HTTP://Example.com:8080/a": "http://example.com:8080/a",
            "example.com:443/a": "https://example.com:443/a",
            "https://bücher.de/path": "https://xn--bcher-kva.de/path",
            "https://example.com/?#": "https://example.com/?#",
            "https://example.com:00443/a": "https://example.com:00443/a",
        }
        for given, expected in cases.items():
            with self.subTest(given=given):
                self.assertEqual(normalize_url(given), expected)
                self.assertEqual(normalize_url(expected), expected)

    def test_ip_literals_preserve_spelling_but_group_canonically(self):
        self.assertEqual(normalize_url("192.0.2.10/verify"), "https://192.0.2.10/verify")
        self.assertEqual(
            normalize_url("https://[2001:DB8::1]:443/a"), "https://[2001:db8::1]:443/a"
        )
        self.assertEqual(normalize_url("https://[::ffff:192.0.2.1]"), "https://[::ffff:192.0.2.1]")
        self.assertEqual(
            domain_group("https://[2001:db8::1]/a"),
            domain_group("http://[2001:0db8:0:0:0:0:0:1]/b"),
        )

    def test_rejects_malformed_schemes_credentials_hosts_ports_and_escapes(self):
        invalid = [
            "javascript:alert(1)",
            "ftp://example.com",
            "https:example.com",
            "//example.com",
            "https://user:pass@example.com",
            "https://exa mple.com",
            "https://example.com\\@evil.com",
            "https://example.com\n",
            "https://example..com",
            "https://999.1.1.1",
            "https://01.2.3.4",
            "https://localhost",
            "https://example.com:0",
            "https://example.com:65536",
            "https://example.com:abc",
            "https://[2001:::1]",
            "https://[invalid]",
            "https://-bad.example",
            "https://example.com/%zz",
            "https://example.com/a[b]",
            "https://example.com/#first#second",
            "https://example.com/<tag>",
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(URLValidationError):
                normalize_url(value)

    def test_utf16_limit_and_surrogates_match_android_length_semantics(self):
        prefix = "https://example.com/"
        limit = prefix + "a" * (4096 - len(prefix))
        self.assertEqual(normalize_url(limit), limit)
        for value in [
            limit + "a",
            prefix + "😀" * 2100,
            prefix + "\ud800",
            prefix + "\udfff",
            None,
            123,
        ]:
            with self.subTest(kind=type(value).__name__), self.assertRaises(URLValidationError):
                normalize_url(value)
        accepted = prefix + "😀" * ((4096 - len(prefix)) // 2)
        self.assertEqual(normalize_url(accepted), accepted)

    def test_parsed_partitions_include_query_exclude_fragment(self):
        parsed = parse_url("https://a.b.example.co.uk/p1?q=2#f3")
        self.assertEqual(parsed.registered_domain, "example.co.uk")
        self.assertEqual(parsed.domain_label, "example")
        self.assertEqual(parsed.subdomain, "a.b")
        self.assertEqual(parsed.suffix, "co.uk")
        self.assertEqual(parsed.path_query, "/p1?q=2")
        self.assertFalse(parsed.is_ip)

    def test_offline_private_suffix_and_unknown_domain_grouping(self):
        self.assertEqual(domain_group("https://a.example.co.kr"), "example.co.kr")
        self.assertEqual(domain_group("https://a.example.co.uk"), "example.co.uk")
        self.assertEqual(domain_group("https://a.project.github.io"), "project.github.io")
        self.assertNotEqual(
            domain_group("https://one.github.io"), domain_group("https://two.github.io")
        )
        self.assertEqual(domain_group("https://a.brand.example"), "brand.example")

    def test_no_dns_connections_or_suffix_downloads(self):
        with patch.object(
            socket, "getaddrinfo", side_effect=AssertionError("No DNS")
        ), patch.object(socket, "create_connection", side_effect=AssertionError("No connection")):
            self.assertEqual(
                domain_group("https://a.uniqueoffline-check.co.uk"), "uniqueoffline-check.co.uk"
            )
            self.assertEqual(domain_group("https://[2001:db8::f]"), "2001:db8::f")


if __name__ == "__main__":
    unittest.main()
```

## server/train.py

```python
import argparse, json, sys
from linkguard.training import train_model, TrainingDataError


def main(argv=None):
    p = argparse.ArgumentParser(description="LinkGuard 재구성본 Random Forest 학습")
    p.add_argument("--csv", required=True)
    p.add_argument("--output", default="artifacts/linkguard.joblib")
    p.add_argument("--report", default="artifacts/metrics.json")
    p.add_argument("--cv-folds", type=int, default=0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--test-size", type=float, default=0.2)
    p.add_argument("--trees", type=int, default=200)
    p.add_argument("--model-version")
    a = p.parse_args(argv)
    try:
        r = train_model(
            a.csv,
            a.output,
            a.report,
            cv_folds=a.cv_folds,
            seed=a.seed,
            test_size=a.test_size,
            trees=a.trees,
            model_version=a.model_version,
        )
    except (TrainingDataError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps(r["holdout"], ensure_ascii=False))
    print("입력 데이터의 독립 평가 결과이며 실제 운영 성능을 보장하지 않습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## settings.gradle.kts

```kotlin
pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "LinkGuard-Rebuilt"
include(":app")
```
