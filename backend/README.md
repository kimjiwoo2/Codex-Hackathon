# Backend

가벼운 데모를 위한 FastAPI 기반 모놀리식 HTTP API입니다. 의존성·가상환경·잠금 파일은 `uv`로 관리합니다.
현재 백엔드는 Neon Postgres, TMAP 보행 경로 API, OpenAI 비전 API, AWS Lambda(Function URL + Mangum) 배포를 기준으로 구현을 준비합니다.

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

## 환경 변수

로컬 개발은 `.env.example`을 복사해 `.env`를 만들고 실제 값을 채웁니다.

```bash
cp .env.example .env
```

| 키 | 용도 |
| --- | --- |
| `OPENAI_API_KEY` | 도로 상황 판단·상품 확인용 OpenAI API 키 |
| `OPENAI_VISION_MODEL` | 비전 추론에 사용할 모델 이름 |
| `TMAP_APP_KEY` | TMAP 보행 경로 API 앱 키 |
| `DATABASE_URL` | 애플리케이션 런타임용 Neon pooled 연결 문자열 |
| `DATABASE_URL_DIRECT` | 스키마 작업용 direct 연결 문자열 |
| `APP_ENV` | 실행 환경 식별자 |
| `CORS_ALLOW_ORIGINS` | 허용할 프런트엔드 origin 목록 |
| `LOCATION_OFF_ROUTE_METERS` | 경로 이탈 판단 거리 임계값 |
| `LOCATION_WRONG_WAY_DEGREES` | 역방향 판단 각도 임계값 |
| `LOCATION_EVENT_COOLDOWN_SECONDS` | 부모 알림 중복 방지 시간 |
| `MISSION_JOIN_CODE_TTL_MINUTES` | 참여 코드 유효 시간 |

## 명령

```bash
uv run ruff format .              # 코드 포맷
uv run ruff check .               # 린트
uv run pytest                     # 테스트
uv run pytest tests/unit          # 단위 테스트
uv run pytest tests/integration   # 통합 테스트
uv run uvicorn app.main:app --reload  # 로컬 서버
uv lock                           # 잠금 파일 갱신
```

## 구조

```text
src/app/
├── api/           # HTTP 라우트와 라우터 조합
├── core/          # 설정, 로깅, 공통 인프라 진입점
├── db/            # SQLAlchemy 세션·모델 베이스
├── integrations/  # TMAP, OpenAI 등 외부 연동 어댑터
├── schemas/       # API 요청·응답 모델
├── services/      # 비즈니스 규칙과 흐름 조합
├── repositories/  # 향후 DB·외부 저장소 어댑터
└── main.py        # FastAPI 애플리케이션 조립
tests/
├── unit/          # 네트워크·DB 없이 실행하는 규칙 및 스키마 테스트
└── integration/   # 애플리케이션 경계를 통과하는 API 테스트
```

`repositories/`는 데이터베이스 또는 외부 저장소를 감싸는 경계입니다. 구현 단계에서는 `services/`가 비즈니스 규칙을 소유하고 `integrations/`가 TMAP/OpenAI 호출을 캡슐화하도록 유지합니다.

## API 계약

### `GET /health`

서비스가 요청을 처리할 수 있는지 확인합니다.

```json
{
  "status": "ok"
}
```

## 구현 기준 의존성

| 패키지 | 목적 |
| --- | --- |
| `fastapi` | HTTP API |
| `sqlalchemy`, `psycopg[binary]` | Neon Postgres 영속성 |
| `httpx` | TMAP/OpenAI HTTP 호출 |
| `openai` | 도로 상황 판단·상품 확인 |
| `python-multipart` | 이미지 업로드 요청 처리 |
| `pydantic-settings` | 환경 변수 설정 로딩 |
| `mangum` | AWS Lambda ASGI 어댑터 |
| `pytest`, `pytest-asyncio` | 비동기 서비스·API 테스트 |
| `uvicorn` | 로컬 개발 서버 |

현재 저장소에는 아직 데이터베이스 스키마, 외부 연동 구현, 마이그레이션, 시드 데이터가 없습니다. 이후 실제 기능을 추가할 때 이 문서와 `docs/spec.md`, `docs/architecture.md`를 함께 갱신합니다.
