# Backend

가벼운 데모를 위한 FastAPI 기반 모놀리식 HTTP API입니다. 의존성·가상환경·잠금 파일은 `uv`로 관리합니다.

## 요구 사항

- [uv](https://docs.astral.sh/uv/)
- Python 3.12 이상 (`uv`가 없으면 설치·관리할 수 있음)

## 시작하기

```bash
cd backend
uv sync --all-groups
uv run uvicorn app.main:app --reload
```

서버는 기본적으로 `http://127.0.0.1:8000`에서 실행됩니다. 대화형 API 문서는 `/docs`에서 확인할 수 있습니다.

## 명령

```bash
uv run ruff format .              # 코드 포맷
uv run ruff check .               # 린트
uv run pytest                     # 테스트
uv run pytest tests/unit          # 단위 테스트
uv run pytest tests/integration   # 통합 테스트
uv run uvicorn app.main:app --reload  # 로컬 서버
```

## 구조

```text
src/app/
├── api/           # HTTP 라우트와 라우터 조합
├── schemas/       # API 요청·응답 모델
├── repositories/  # 향후 DB·외부 저장소 어댑터
└── main.py        # FastAPI 애플리케이션 조립
tests/
├── unit/          # 네트워크·DB 없이 실행하는 규칙 및 스키마 테스트
└── integration/   # 애플리케이션 경계를 통과하는 API 테스트
```

`repositories/`는 향후 데이터베이스 또는 외부 저장소가 도입될 때 구현을 추가할 경계입니다. 현재는 저장소가 없으므로 연결 설정이나 가짜 구현을 만들지 않습니다.

## API 계약

### `GET /health`

서비스가 요청을 처리할 수 있는지 확인합니다.

```json
{
  "status": "ok"
}
```

현재 데모에는 필수 환경 변수, 데이터베이스, 마이그레이션 또는 시드 데이터가 없습니다. 이후 외부 연동이나 비밀값이 필요해지면 `.env.example`과 이 문서에 함께 추가합니다.
