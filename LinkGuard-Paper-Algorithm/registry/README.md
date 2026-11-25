# 모델 DB 자리

이 디렉터리는 기본 SQLite 모델 레지스트리의 위치입니다. 아래 명령으로 로컬 DB를 만드세요.

```sh
python modelctl.py --db registry/models.sqlite3 init
```

가중치는 DB에 직접 넣지 않고, DB에는 모델의 이름·버전·종류·경로·SHA-256·입력 스키마·활성 상태를 보관합니다. 제공된 `model_registry.sql`에서 테이블 구조를 확인할 수 있습니다.

학습 데이터 DB는 별도 학습 프로그램이 사용합니다. 기존 MySQL/PostgreSQL DB를 모델 선택에 쓰려면 `ModelRegistry.get_active()`를 구현하고 `create_app(registry=...)`에 전달하세요. 등록·활성화의 쓰기 동작은 해당 DB에서 원자적 전환을 유지하도록 별도로 구현합니다.

실제 DB 파일과 DB 비밀번호는 Git/소스 ZIP에 포함하지 않습니다.
