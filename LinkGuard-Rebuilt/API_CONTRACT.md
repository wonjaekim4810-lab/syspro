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
