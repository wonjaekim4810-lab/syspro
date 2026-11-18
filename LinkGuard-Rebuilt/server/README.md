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
