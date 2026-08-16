# Backend

가벼운 데모를 위한 FastAPI 기반 모놀리식 HTTP API입니다. 의존성·가상환경·잠금 파일은 `uv`로 관리합니다.
현재 백엔드는 Neon Postgres, TMAP 보행 경로 API, OpenAI 비전 API, AWS Lambda(Function URL + Mangum) 배포를 기준으로 통제된 데모를 제공합니다.

## 요구 사항

- [uv](https://docs.astral.sh/uv/)
- Python 3.12 이상 (`uv`가 없으면 설치·관리할 수 있음)

## 시작하기

```bash
cd backend
uv sync --all-groups
uv run uvicorn --app-dir src --env-file .env app.main:app --reload
```

서버는 기본적으로 `http://127.0.0.1:8000`에서 실행됩니다. 대화형 API 문서는 `/docs`에서 확인할 수 있습니다.
`--app-dir src`는 `src` layout의 `app` 패키지를 import 경로에 추가합니다.

## 환경 변수

로컬 개발은 `.env.example`을 복사해 `.env`를 만들고 실제 값을 채웁니다.

```bash
cp .env.example .env
```

`Settings`는 의도적으로 `env_file=None`이므로 `.env`를 직접 읽지 않습니다. 위의 Uvicorn
명령은 `--env-file .env`로 값을 process environment에 주입합니다. `.env`를 사용하지 않는
로컬 셸과 AWS Lambda는 동일한 이름의 환경 변수를 직접 주입해야 하며, 값이 들어 있는 파일을
저장소·로그·issue·PR에 남기지 않습니다.

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

`APP_ENV=demo`는 해커톤 통제 데모 전용 모드입니다. 첫 mission API 요청에서만
`Base.metadata.create_all()`로 세 테이블을 준비합니다. Lambda는 ASGI lifespan을 끄므로
startup hook에 의존하지 않습니다. `production` 등 다른 환경에서는 애플리케이션이 schema를
만들지 않으며, 배포자가 승인된 schema 절차를 수행해야 합니다.

### 데모 고정 안전 기준

이번 데모의 길안내는 경로 이탈 30m, 역방향 120도, 연속 유효 GPS 2회라는 고정 기준을
사용합니다. 따라서 `LOCATION_OFF_ROUTE_METERS`, `LOCATION_WRONG_WAY_DEGREES`,
`LOCATION_EVENT_COOLDOWN_SECONDS`는 현재 P0 서비스의 runtime override가 아닙니다. 값을
바꿔도 데모 안전 기준을 넓히지 않으며, 임계값 변경은 별도 검증 범위에서만 수행합니다.

도로 비전은 `STOP`, `CAUTION`, `UNKNOWN`만 반환합니다. OpenAI를 사용할 수 없으면
`UNKNOWN`과 멈춰서 직접 확인하라는 고정 문구로 낮아지며, 횡단 허가 판단이나 원본 이미지는
응답·이벤트·저장소에 남기지 않습니다. 시연은 보호자 동행과 식별정보가 없는 통제 이미지로
제한합니다.

## 명령

```bash
uv run ruff format .              # 코드 포맷
uv run ruff check .               # 린트
uv run pytest                     # 테스트
uv run pytest tests/unit          # 단위 테스트
uv run pytest tests/integration   # 통합 테스트
uv run uvicorn --app-dir src --env-file .env app.main:app --reload  # 로컬 서버
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

`main.create_app()`은 하나의 settings, engine, session factory, repository, 역할 token verifier,
TMAP/OpenAI adapter 및 모든 feature service를 앱 수명 동안 공유하도록 조립합니다. import와
`/health` 요청은 비밀값이나 DB 접속을 요구하지 않으며, 테스트는 SQLite와 typed adapter double을
주입해 실제 라우터 조립 경로를 검증합니다.

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

외부 Neon·TMAP·OpenAI·AWS smoke는 해당 자격 증명과 승인된 Function URL이 있는 환경에서만
수행합니다. 키나 endpoint를 issue, PR, 로그에 기록하지 않습니다. 자격 증명이 없을 때는 mock
E2E 통과와 `SMOKE_BLOCKED_BY_ENV`를 분리해 기록합니다.
