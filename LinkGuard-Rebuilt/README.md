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
