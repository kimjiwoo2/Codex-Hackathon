# Codex Hackathon

5시간 내 빠른 개발을 위한 프런트엔드·백엔드 모노레포입니다.
프런트엔드는 Expo SDK 54 기반이며, 백엔드는 `uv`로 관리하는 FastAPI 모놀리스입니다.

## 저장소 구조

```text
.
├── frontend/        # Expo 프런트엔드 애플리케이션
├── backend/         # 백엔드 애플리케이션 영역
├── docs/            # 스펙, 아키텍처, 의사결정, 개발 규칙
├── .github/         # GitHub 협업 템플릿
└── AGENTS.md        # 작업 전 확인할 문서 인덱스
```

## 프런트엔드 실행

```bash
cd frontend
npm ci
npm start
```

세부 명령과 구조는 [`frontend/README.md`](frontend/README.md)를 확인합니다.

## 백엔드 실행

```bash
cd backend
uv sync --all-groups
cp .env.example .env  # 실제 로컬 값으로 바꾼 뒤 사용; .env는 커밋하지 않음
uv run uvicorn --app-dir src --env-file .env app.main:app --reload
```

`src` layout은 `--app-dir src`가 필요합니다. `Settings`는 `.env`를 직접 읽지 않으므로,
로컬 `.env`는 Uvicorn의 `--env-file .env`로 process environment에 주입합니다. 셸과 AWS
Lambda에서는 같은 이름의 환경 변수를 직접 주입합니다. 세부 명령과 API 계약은
[`backend/README.md`](backend/README.md)를 확인합니다.

## 문서 진입점

- 프로젝트 문서: [`docs/README.md`](docs/README.md)
- 작업자 인덱스: [`AGENTS.md`](AGENTS.md)
- 제품 스펙: [`docs/spec.md`](docs/spec.md)
- 아키텍처: [`docs/architecture.md`](docs/architecture.md)
