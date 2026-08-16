# Documentation

`docs/`는 제품과 구현에 관한 단일 기준점(Single Source of Truth)이다.

| 문서 | 역할 | 갱신 시점 |
| --- | --- | --- |
| [`spec.md`](spec.md) | 목표, 사용자, 범위, 완료 조건 | 요구사항 변경 시 |
| [`architecture.md`](architecture.md) | 시스템 경계, 데이터 흐름, 품질 속성 | 구조 변경 시 |
| [`backend-parallel-implementation-plan.md`](backend-parallel-implementation-plan.md) | 병렬 구현 순서, 이슈 분해, 세션 작업 규칙 | 구현 착수 전/범위 조정 시 |
| [`decisions/`](decisions/README.md) | 주요 의사결정과 근거(ADR) | 중요한 결정 확정 시 |
| [`conventions/development.md`](conventions/development.md) | 공통 개발·검증 규칙 | 개발 방식 변경 시 |
| [`conventions/git.md`](conventions/git.md) | 브랜치, 커밋, PR 규칙 | 협업 방식 변경 시 |

## 빠른 개발 중 문서 우선순위

1. `spec.md`의 목표와 비목표를 먼저 고정한다.
2. 되돌리기 어려운 선택만 ADR로 기록한다.
3. 실제 구조가 바뀐 경우에만 아키텍처 문서를 갱신한다.
4. 회의록 대신 결정, 근거, 후속 작업만 간결하게 남긴다.
