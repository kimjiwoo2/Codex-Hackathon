# Architecture Decision Records

ADR은 팀 전체에 영향을 주거나 나중에 되돌리기 비싼 결정을 짧게 기록한다.
단순 구현 세부사항이나 쉽게 바꿀 수 있는 선택은 기록하지 않는다.

## 파일 규칙

- 파일명: `NNNN-short-title.md` (예: `0001-select-frontend-stack.md`)
- 번호는 순차 증가하며 기존 번호를 재사용하지 않는다.
- 상태: `Proposed`, `Accepted`, `Superseded`, `Deprecated`
- 결정이 대체되면 기존 ADR을 삭제하지 않고 새 ADR을 링크한다.

## 템플릿

새 ADR은 [`template.md`](template.md)를 복사해 작성한다.

## Decision log

| ADR | 상태 | 결정일 | 제목 |
| --- | --- | --- | --- |
| [`0001`](0001-expo-frontend.md) | Accepted | 2026-08-16 | Expo 기반 프런트엔드 구성 |
