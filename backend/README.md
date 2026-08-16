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
uv run uvicorn app.main:app --reload  # 로컬 서버
```

## API 계약

### `GET /health`

서비스가 요청을 처리할 수 있는지 확인합니다.

```json
{
  "status": "ok"
}
```

현재 데모에는 필수 환경 변수, 데이터베이스, 마이그레이션 또는 시드 데이터가 없습니다. 이후 외부 연동이나 비밀값이 필요해지면 `.env.example`과 이 문서에 함께 추가합니다.
