# AGENTS.md

이 파일은 규칙의 원문이 아니라 작업자가 필요한 문서를 빠르게 찾기 위한 인덱스다.
세부 내용은 `docs/`의 원문을 수정하고, 이 인덱스에는 링크만 유지한다.

## 작업 전 필수 확인

1. [`docs/spec.md`](docs/spec.md) — 목표, 범위, 완료 조건
2. [`docs/architecture.md`](docs/architecture.md) — 시스템 경계와 의존 방향
3. [`docs/conventions/development.md`](docs/conventions/development.md) — 공통 개발 규칙
4. [`docs/conventions/git.md`](docs/conventions/git.md) — 브랜치, 커밋, PR 규칙
5. [`docs/decisions/README.md`](docs/decisions/README.md) — 확정된 의사결정 기록

## 영역별 진입점

- 프런트엔드: [`frontend/README.md`](frontend/README.md)
- 백엔드: [`backend/README.md`](backend/README.md)
- 전체 문서 지도: [`docs/README.md`](docs/README.md)

## 문서 갱신 원칙

- 요구사항이 바뀌면 코드보다 먼저 `docs/spec.md`를 갱신한다.
- 시스템 경계나 데이터 흐름이 바뀌면 `docs/architecture.md`를 함께 갱신한다.
- 되돌리기 어렵거나 팀 전체에 영향을 주는 결정은 ADR로 남긴다.
- 문서와 구현이 충돌하면 같은 PR에서 함께 정합성을 맞춘다.
