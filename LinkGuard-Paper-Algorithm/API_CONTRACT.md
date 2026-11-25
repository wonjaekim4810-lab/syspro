# LinkGuard 예측 API와 외부 모델 연결 규격

`POST /predict`, JSON 요청 `{"url":"https://www.example.com"}`를 사용합니다. 입력은 HTTP(S) URL만, 정규화 전후4096UTF-16단위 이내입니다. 계정 정보·제어문자·잘못된 포트·IP·URL 형식은 거부합니다. URL은 문자열로만 분석하며 직접 방문하지 않습니다.

성공은 HTTP200 `application/json`:

```json
{
  "url":"https://www.example.com",
  "status":"caution",
  "score":57,
  "reasons":["URL에서 관찰한 특징입니다. 모델의 기여도 설명이 아닙니다."],
  "model_version":"ml-v1"
}
```

위 값은 형식 설명용이며 해당 URL의 실제 모델 예측이 아닙니다. `url`은 요청을 정규화한 문자열과 동일합니다. `status`는 `safe,caution,danger`, `score`는0~100정수, `reasons`는 비어 있지 않은 문자열1~12개(각500자 이하), `model_version`은영숫자로 시작하는최대120자 영숫자/._- 문자열입니다. 점수와40/80경계는 보정된 확률·검증된 운영기준이 아닙니다.

오류 입력422, 학습 모델/DB/어댑터 미준비503, 본문16KiB초과413, 추론4슬롯 초과503입니다. 실패하면 가짜 판정이나 다른 모델의 결과를 대신 만들지 않습니다. 기본 DB 선택은 `LINKGUARD_MODEL_DB` 환경 변수, 기본 경로는 `registry/models.sqlite3`입니다. `GET /health`는 모델 사용 가능 여부만 반환하며 내부 경로·입력 URL을 노출하지 않습니다.

ML 입력은 `FeatureExtractor.vector(url)`의40개 특징 순서이고, 라벨0정상/1피싱입니다. sklearn 호환 추정기는 NumPy`[batch,40]` 입력과 `predict_proba`를 지원해야 하며 전처리가 있다면 학습된 Pipeline 안에 포함해야 합니다. 기본 ONNX 입력은float32`[batch,40]`, 출력하나는`[1,2]`정상/피싱확률 또는`[1,1]`/`[1]`단일피싱확률입니다. 원시URL·문자토큰 기반 모델은 `CustomURLTextAdapter`를 구현하기 전에는 사용할 수 없습니다.

Kotlin 앱은 서버가 보낸 등급을 그대로 표시하며 앱의 로컬 규칙32/65경계로 재분류하지 않습니다. HTTPS 서버만 허용하므로 유효한 인증서의 서버/리버스 프록시를 준비해야 합니다.
