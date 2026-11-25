# LinkGuard 논문 기반 URL 알고리즘 + 외부 학습 모델 연결

Sahingoz, Buber, Demir, Diri(2019), *Machine learning based phishing detection from URLs*, ESWA117:345–357, DOI `10.1016/j.eswa.2018.09.029`의 WDM·RWDM·MAM 흐름과 수치 특징 설계를 참고한 Python 구현입니다.

**이 패키지는 학습된 운영 모델을 포함하지 않습니다.** 사용자가 DB에 모은 데이터로 ML/DL을 별도로 학습하고, 학습된 결과를 등록해 사용할 수 있도록 모델 연결 자리를 제공합니다. DB 자체가 학습을 수행하는 것은 아닙니다. DB에는 모델 종류·버전·파일 위치·입력 규격·지문·활성 여부를 보관하고, 가중치는 로컬 파일로 보관하는 SQLite 예제를 제공합니다. 기존 MySQL/PostgreSQL 등을 쓰려면 `ModelRegistry.get_active()` 구현만 연결합니다.

원 논문 코드·사전·말뭉치·데이터를 그대로 재현한 것이 아닙니다. 원 논문의 97.98%는 이 프로그램의 측정 정확도가 아닙니다. 40개 특징 중 원 표의 Alexa 두 개는 현재 사용 가능한 HTTPS/IP 두 특징으로 대체했습니다. 사전·문자쌍 자료와 임계값은 실험적 설계입니다. 실제 안전성·도메인 소유권·웹페이지 내용·리디렉션 목적지는 확인하지 않으며, 분석 중 사이트에 접속하거나 DNS를 조회하지 않습니다.

## 1. 설치와 모델 없는 특징 확인

Python3.11 이상이 필요합니다. Windows PowerShell에서:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python explain_url.py "http://securelogin.example/verify"
python detector.py features "https://www.example.com"
```

Linux/macOS는 `python3 -m venv .venv`와 `source .venv/bin/activate`를 사용합니다. `requirements.txt`는 실행용, `requirements-dev.txt`는 테스트 포함입니다. 설치 시 인터넷 연결이 필요하지만 URL 분석 시 사전나 Public Suffix List를 다운로드하지 않습니다.

`explain_url.py`는 정규화 → 도메인 구분 → 토큰 → WDM 분리 → RWDM 문자쌍 점수 → MAM 유사어 → 40개 특징을 JSON으로 보여줍니다. 이것은 모델 예측이나 모델 기여도 설명이 아니며 피싱 점수를 만들지 않습니다. 실제 코드 흐름과 예시는 별도 한국어 PDF 설명서를 참고하세요.

## 2. 내가 학습한 ML 모델 넣기

입력은 `FeatureExtractor.vector(url)`가 반환하는 **동일한 순서의 40개 수치 특징**입니다. 정상 라벨은0, 피싱 라벨은1입니다. 외부 학습 코드에서도 이 추출기를 사용하세요. 스케일링 등 전처리가 필요하면 학습된 sklearn Pipeline 안에 함께 넣어야 합니다. DataFrame 전용 전처리나 다른 토크나이저가 필요한 모델은 기본 어댑터에 바로 넣지 않고 사용자 어댑터를 만듭니다.

다음은 이미 학습한 sklearn 추정기/Pipeline을 저장하는 예시입니다. 어떤 ML 알고리즘을 학습할지는 사용자 영역입니다.

```python
from pack_joblib import export_pretrained

# trained_model = DB에서 읽은 데이터로 별도 학습한 모델
# trained_model은 NumPy[batch,40] 입력, classes_=[0,1], predict_proba 지원 필요
export_pretrained(trained_model, "artifacts/my-ml-v1.joblib", "ml-v1")
```

신뢰할 수 있는 raw joblib 파일을 이미 저장했다면:

```powershell
python pack_joblib.py --input trained-model.joblib --output artifacts/my-ml-v1.joblib --version ml-v1
python modelctl.py --db registry/models.sqlite3 init
python modelctl.py --db registry/models.sqlite3 register --name url-ml --version ml-v1 --backend joblib --artifact artifacts/my-ml-v1.joblib --activate
python modelctl.py --db registry/models.sqlite3 list
python detector.py predict "https://www.example.com" --db registry/models.sqlite3
```

포장은 모델의 특징 개수·이름(있는 경우)·클래스 순서를 확인하지만, 실제 학습한 열의 의미까지 추론할 수는 없습니다. 올바른 특징 순서로 학습했는지는 학습 담당자가 보장해야 합니다. `joblib`은 Python 코드를 실행할 수 있으므로 직접 생성했거나 신뢰하는 로컬 파일만 사용하세요. HTTP 모델 업로드 기능은 제공하지 않습니다.

## 3. 별도 학습한 DL 모델 넣기

두 연결 경로를 제공합니다.

| 연결 자리 | 실제 지원 계약 | 사용자 작업 |
| --- | --- | --- |
| `OnnxFeatureAdapter` | float32`[batch,40]` 입력 하나, 확률 텐서 출력 하나 | 동일40특징으로 학습한 신경망 등을 ONNX로 내보내기 |
| `CustomURLTextAdapter` | 기본은 미구현·실패 처리 | URL 문자열/CNN/RNN/Transformer의 토크나이저·전처리·가중치·추론 함수를 직접 연결 |

ONNX 사용 시에만 다음 의존성을 설치합니다.

```powershell
python -m pip install -r requirements-onnx.txt
python modelctl.py --db registry/models.sqlite3 register --name url-dl --version dl-v1 --backend onnx --artifact artifacts/my-dl-v1.onnx --activate
```

기본 ONNX 출력은 `[1,2]` 정상/피싱 클래스 확률(합1, 기본 피싱 인덱스1)입니다. 클래스 위치가 반대면 `--positive-index 0`을 지정합니다. `[1,1]` 또는 `[1]` 출력은 **단일 피싱 확률**로 해석하며 이때 인덱스 옵션은 사용하지 않습니다. 출력은 이미 sigmoid/softmax를 통과한 0~1이어야 하며 로짓을 자동 변환하지 않습니다. 입력은 반드시40열이며, 원시 URL 문자·토큰 ID 모델을 이 슬롯에 넣으면 안 됩니다.

원시 URL 기반 모델 연결 자리는 `linkguard/adapters.py`의 `CustomURLTextAdapter`입니다. `load(record)`에서 저장한 토크나이저와 가중치를 로드하고, `probability(url, vector)`에서 학습 때와 같은 URL 전처리로0~1 피싱 출력을 반환하도록 구현합니다. 현재는 명시적으로 `ModelUnavailableError`를 발생시켜서 연결 전 가짜 점수를 만들지 않습니다. 다음 명령은 **등록 자리만 만드는 예시이며 활성화는 구현 완료 후에만 성공**합니다.

```powershell
python modelctl.py register --name url-transformer --version custom-v1 --backend custom --input-kind url_text --artifact artifacts/my-trained-weights.bin
```

## 4. 기존 DB와 연결

SQLite 기본 스키마는 `model_registry.sql`에 있습니다. `model_registry` 레코드 필드는 `id,name,version,backend,input_kind,artifact_path,sha256,feature_schema_version,resource_fingerprint,positive_class_index,active`입니다. SHA-256은 등록 시 실제 파일에서 계산합니다. 활성 모델은 한 개만 유지하며, 먼저 파일·스키마·실제 추론 호출을 검사한 후 트랜잭션으로 교체합니다. 검증 실패 시 기존 활성 모델은 유지됩니다.

기존 DB 연결 어댑터의 최소 계약:

```python
from linkguard.registry import ModelRecord
from server import create_app

class YourDBRegistry:
    def get_active(self) -> ModelRecord | None:
        # 실제 DB에서 활성 모델 1행을 읽어 ModelRecord로 매핑하세요.
        # DB 비밀번호는 코드/공개 저장소가 아니라 서버 비밀 설정으로 관리하세요.
        raise NotImplementedError("실제 DB 조회 코드를 연결하세요.")

app = create_app(registry=YourDBRegistry())
```

실제 DB 스키마가 다르면 `get_active()` 내부에서 매핑하면 됩니다. 가중치를 DB BLOB으로 저장하는 방식은 현재 구현하지 않았습니다. 필요하면 별도 안전한 파일 적재/로더 어댑터를 구현해야 합니다.

**모델 파일은 버전별로 불변 파일로 보관하세요.** 서버는 활성 DB 레코드를 요청마다 확인하고 레코드가 바뀌면 모델을 검증·로드합니다. 이미 메모리에 로드된 파일의 변경을 매 요청 감시하지는 않습니다. 같은 파일을 덮어쓰기보다 새 파일·새 버전·새 레코드를 등록한 뒤 활성화하세요. 재시작하거나 새 레코드 선택 시 파일 SHA-256이 다르면 사용하지 않습니다. 잘못된 새 모델로 전환되었을 때 이전 모델의 점수를 몰래 대신 반환하지 않습니다.

## 5. 서버와 Kotlin 연결

기본 서버는 DB 레지스트리를 사용하며 운영 모델이 없으면 `/predict`는503을 반환합니다.

```powershell
$env:LINKGUARD_MODEL_DB = "registry/models.sqlite3"
uvicorn server:app --host 127.0.0.1 --port 8090 --no-access-log
```

Linux/macOS는 `export LINKGUARD_MODEL_DB=registry/models.sqlite3`를 사용합니다. `GET /health`는 `ready` 또는 `model_unavailable`을 반환합니다. 서버의 실제 모델 활성화 후 Kotlin 앱 설정에 유효한 인증서가 있는 HTTPS 기본 주소를 저장하고 원격 분석을 켜세요. 위 HTTP 주소는 개발 PC 로컬 확인용이며 Android 기기에서 개발 PC의127.0.0.1로 직접 연결할 수 없습니다. HTTPS 리버스 프록시·서버 인증·요청 제한은 운영 환경에서 구성해야 합니다.

```json
{"url":"https://www.example.com"}
```

성공 응답은 `url,status,score,reasons,model_version`입니다. 응답 `score`는 모델 피싱 클래스 출력을100배 반올림한 정수이고, `safe`<40 / `caution`40~79 / `danger`≥80으로 표시합니다. 이 기준은 운영 검증 전의 시제품 기준이며 보정된 실제 피싱 확률이나 안전 보증이 아닙니다. `reasons`는 관찰된 URL 특징으로 실제 모델 기여도를 계산한 것이 아닙니다. 입력 오류422, 모델 미준비503, 본문16KiB초과413, 동시 추론4개를 넘으면503입니다. 입력 URL이나 원문 메시지를 로그로 출력하지 않습니다.

이전 호환용 직접 파일 CLI는 `python detector.py predict URL --model artifacts/linkguard.joblib`입니다. 이는 기존 RF 전용 로더를 명시적으로 사용하는 옵션이며 기본 DB 경로와 별개입니다. 서버에서도 `create_app(model_path=...)`를 직접 지정했을 때만 기존 로더를 사용합니다.

## 6. 선택 사항: 이 패키지에서 RF 후보 모델 학습

사용자가 별도 DB 학습을 할 계획이라면 이 단계는 생략하면 됩니다. `train.py`는 정상0/피싱1 `url,label` CSV에서 RF 후보를 학습하는 참고 코드입니다. 모델 없는 특징 분석·DB 레지스트리·외부 학습 모델 연결과 분리되어 있습니다.

```powershell
python train.py --csv data/urls.csv --trees 200 --cv-folds 5 --output artifacts/linkguard.joblib --report artifacts/metrics.json --model-version rf-v1
```

최소 실행 조건은 중복 제거 후20URL, 라벨별5URL·4등록도메인입니다. 이는 유효한 연구 검증에 충분한 규모라는 뜻이 아닙니다. 같은 등록 도메인이 학습·보류 평가에 섞이지 않도록 그룹 분리하고, CV는 훈련 부분에만 적용합니다. 저장 모델은 보류 평가셋으로 재학습하지 않습니다. 보고서의 이진 RF `predict` 지표와40/80 화면 정책 지표를 구분합니다. 도메인 분리만으로 시간·캠페인·공통 템플릿 누수가 모두 제거되지는 않습니다.

## 7. 파일 안내와 검증 범위

- `linkguard/urltools.py`: URL 정규화·오프라인 도메인 구분
- `linkguard/nlp.py`: WDM·RWDM·MAM
- `linkguard/features.py`: 순서가 고정된40개 특징
- `linkguard/registry.py`: DB 교체 인터페이스와 SQLite 구현
- `linkguard/adapters.py`: ML·ONNX·사용자 URL 모델 연결 자리
- `linkguard/registered_detector.py`: 활성 모델 선택·캐시·공통 응답
- `pack_joblib.py`: 외부 학습 모델 포장
- `modelctl.py`: 로컬 DB 등록·활성화
- `explain_url.py`: 모델 없는 단계별 설명
- `server.py`: Kotlin 호환 API
- `train.py`: 선택적 RF 학습

이전 Kotlin/서버 재구성 폴더는 수정하지 않았습니다. 기본·DB·API 및 실제 ONNX 추론 테스트 59개가 통과했습니다. 실제 ONNX 테스트 3개에는 선택 의존성 `pip install -r requirements-onnx.txt onnx`가 필요합니다. 합성 DB 데이터로 학습한 ML 모델과 ONNX 모델의 등록·활성화 및 HTTP 응답도 확인했습니다. 자세한 설명은 [25쪽 한국어 PDF](docs/LinkGuard_Paper_Algorithm_Guide_KO.pdf)와 `VALIDATION.json`에 있습니다. 테스트 합성 데이터는 프로그램 동작 확인용이며 실제 탐지 성능을 뜻하지 않습니다.
