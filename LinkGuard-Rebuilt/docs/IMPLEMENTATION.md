# 재구성 범위와 검증 기록

이 문서는 현재 재구성본만 설명합니다. 이전 소스·ZIP·APK는 확보되지 않았고 원본 일치 여부를 확인할 수 없습니다. 이전 대화에서 기록한 검사 결과는 아래 결과를 대신하지 않습니다.

| 구성 | 범위 |
| --- | --- |
| Android | Kotlin·Compose 다섯 화면, URL·ZXing QR, 로컬 기록, 명시적 권한 기반 SMS·알림 감지 |
| 로컬 분석 | 구조적 규칙 기반 시제품, AI 판정이나 안전 보증이 아님 |
| Python | WDM·RWDM·MAM 참고 특징, Random Forest 학습·평가, FastAPI API |
| 모델·데이터 | 실제 라벨 검증 데이터와 학습 가중치 미포함 |
| 네트워크 | 명시적으로 서버 분석을 켰을 때 URL만 전송, 대상 사이트 조회 없음 |
| 백그라운드 | Android 수신 이벤트에 따른 최선의 처리, 항상 실행·강제 차단 보장 없음 |

## 현재 검증

| 항목 | 재구성본 결과 |
| --- | --- |
| Python 의존성 설치 | Python 3.12.14의 새 가상환경에서 requirements-dev 설치와 pip check 통과 |
| Python 단위 테스트 | 현재 재구성본 40개 통과: NLP·특징 14 / URL 7 / 학습 8 / 모델·API 11. 실패·오류 없음 |
| Python CLI·HTTP 연동 | 40개 특징 CLI, 합성 URL 80개 학습·훈련 내부 2-fold CV·모델/보고서 저장·CLI 예측 통과. 실제 Uvicorn TCP에서 ready·예측 200·잘못된 URL 422 및 모델 없음 상태·503 확인 |
| Kotlin 컴파일·단위 테스트 | 컴파일 통과. JUnit 16개 통과: UrlTools 6 / RuleAnalyzer 5 / PredictionParser 5, 실패·오류 0 |
| APK 빌드·서명 | assembleDebug 통과. kr.ac.linkguard / versionCode 2 / 0.2.0-rebuilt / minSdk 26 / targetSdk 35. 16,050,127바이트. aapt 메타데이터·apksigner 서명 확인 통과 |
| Android Lint | 오류 0, 경고 4. Compose·core·activity·lifecycle 의존성의 새 버전 안내 |
| Android 실기기·에뮬레이터 화면·권한·QR·SMS | 별도 확인 필요 |
| 실제 정상·피싱 데이터의 독립 평가 | 미수행, 데이터 미제공 |
| 실제 HTTPS 서버와 Android 기기 연결 | 별도 확인 필요 |

규칙 점수, 모델 출력과 40/80 표시 기준은 피싱 확률·보증으로 해석하지 않습니다. 원 논문의 97.98%는 원 실험의 수치입니다. 로컬 영어 자료, 분해 방식, 대체 특징, 도메인 분할과 평가 방식이 원 논문과 다릅니다.

Python 코드는 Black 25.1로 서식을 정리했습니다. 위 테스트는 재구성본에서 직접 실행한 결과이며 원 논문 성능이나 실제 피싱 데이터의 정확도 측정이 아닙니다. 합성 데이터와 테스트 모델은 프로그램 연결 검증용입니다. Python wheel 빌드와 별도 위치에 설치한 패키지의 모듈·언어 리소스 로딩도 통과했습니다.

부모 작업에서 생성하는 `SOURCES.md`는 현재 소스를 대화·문서로 확인하기 위한 묶음입니다. 이를 생성했다는 사실은 영구 다운로드 링크나 원본 복구를 보장하지 않습니다.

## 패키징 산출물

소스·설치 파일은 `LinkGuard-Python-Rebuilt.zip`, `LinkGuard-Kotlin-Python-Rebuilt.zip`, `LinkGuard-debug-Rebuilt.apk` 이름으로 준비합니다. `SOURCES.md`는 소스 전문, `FILES.md`는 파일 목록, `SHA256SUMS.txt`는 체크섬을 확인하는 용도입니다. 실제 생성·검증된 파일은 최종 작업 결과를 기준으로 확인하세요. 이 파일명은 이전 원본을 복원했다는 뜻이 아닙니다.
