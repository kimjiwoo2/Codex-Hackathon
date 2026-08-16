# 백엔드 병렬 구현 계획

> 상태: Active<br>
> 최종 갱신: 2026-08-16

## 1. 목표

3시간 안에 부모/아이 핵심 시나리오를 시연 가능한 수준으로 구현한다.

- 부모가 심부름 생성 후 참여 코드와 진행 상태를 확인한다.
- 아이가 마트까지 이동하고, 상품을 확인하고, 집으로 돌아오는 안내를 받는다.
- 도로 상황 경고와 부모 알림이 동작한다.

## 2. 고정 제약

- 인식 정확도보다 개발 속도를 우선한다.
- AWS 운영 인프라는 최소 가정만 두고, 백엔드 코드 구조와 API 구현에 집중한다.
- 지도는 TMAP, 비전 판단은 OpenAI, DB는 Neon Postgres를 사용한다.
- 도로 판단은 `STOP | CAUTION | UNKNOWN`만 허용한다.
- 부모 화면은 polling, 푸시/백그라운드 알림은 제외한다.

## 3. 구현 순서

### Phase 0 — 선행 기반 작업

이 단계가 끝나야 다른 세션이 충돌 없이 병렬 작업을 시작할 수 있다.

1. 설정/환경 변수 로더 추가
2. DB 엔진, 세션, 모델 베이스 구성
3. 공통 오류 응답과 역할 토큰 검사 유틸 추가
4. 외부 API 클라이언트 인터페이스 골격 추가

### Phase 1 — 병렬 작업 스트림

Phase 0 이후 아래 스트림을 병렬로 진행한다.

| 스트림 | 목표 | 주요 파일 소유권 | 선행 조건 |
| --- | --- | --- | --- |
| A | 미션/참여/부모 조회 API | `api/missions.py`, `services/mission_service.py`, `repositories/mission_*`, `schemas/mission_*` | Phase 0 |
| B | 위치 업데이트와 길안내 | `api/navigation.py`, `services/navigation_service.py`, `integrations/tmap.py`, `schemas/navigation_*` | Phase 0 |
| C | 도로 상황 판단과 부모 알림 | `api/road_checks.py`, `services/road_scene_service.py`, `integrations/openai_vision.py`, `schemas/road_*` | Phase 0 |
| D | 상품 확인과 쇼핑/귀가 상태 전이 | `api/item_checks.py`, `services/item_check_service.py`, `schemas/item_*` | Phase 0, A |
| E | 통합 테스트와 회귀 검증 | `tests/integration/**`, `tests/unit/**` | A, B, C, D |

### Phase 2 — 통합 마감

1. 라우터 조합과 앱 등록 정리
2. `.env.example`, README, 수동 검증 절차 점검
3. 외부 API 실패 시 안전한 fallback 확인

## 4. GitHub 이슈 분해 원칙

- 이슈 하나는 하나의 병렬 스트림만 소유한다.
- 여러 세션이 같은 파일을 동시에 수정하지 않도록 파일 소유권을 먼저 고정한다.
- 공통 파일(`main.py`, `api/router.py`) 수정이 필요하면 가장 마지막 통합 단계에서만 다룬다.
- 각 세션은 자신이 소유한 이슈 번호를 브랜치/커밋/PR 본문에 명시한다.

## 5. 이슈별 상세 작업

### 이슈 1 — 기반 인프라 골격

- `core/settings.py` 환경 변수 로더
- `db/session.py`, `db/base.py`
- 공통 auth/role dependency
- OpenAI/TMAP client protocol 또는 thin wrapper

하위 분해:

- 설정/환경 변수
- DB 세션/베이스
- 공통 예외/토큰 유틸
- 외부 클라이언트 인터페이스

### 이슈 2 — 미션/참여/부모 조회

- 심부름 생성
- 참여 코드 조회·참여
- 부모 snapshot polling API
- 상태 전이 명령

하위 분해:

- mission/item 모델
- repository CRUD
- create/join API
- parent snapshot API

### 이슈 3 — 길안내/경로 이탈 판단

- TMAP 보행 경로 조회
- outbound/return 경로 캐시
- 위치 업데이트 API
- next instruction, off-route, wrong-way 계산

하위 분해:

- TMAP 응답 정규화
- 위치 샘플 누적
- 역방향/이탈 계산
- child guidance 응답 포맷

### 이슈 4 — 도로 상황 판단/알림

- 이미지 업로드 API
- OpenAI 비전 프롬프트와 structured output
- `STOP | CAUTION | UNKNOWN` 정규화
- 부모용 `ROAD_RISK` 이벤트 저장

하위 분해:

- 이미지 입력 스키마
- 모델 응답 정규화
- 안전 문구 매핑
- 이벤트 발행

### 이슈 5 — 상품 확인/쇼핑 완료/귀가

- 상품 확인 API
- `MATCH | SIMILAR | MISMATCH | UNKNOWN` 저장
- 쇼핑 완료 후 `RETURNING` 전환
- 상품 실패와 무관한 귀가 fallback

하위 분해:

- 상품 비교 프롬프트
- 결과 저장
- 상태 전이 규칙
- child speech 문구

### 이슈 6 — 통합 테스트와 시연 검증

- 외부 API mock 통합 테스트
- 상태 흐름 `WAITING → GOING → SHOPPING → RETURNING → COMPLETED`
- README 수동 검증 절차
- 실패 fallback 검증

하위 분해:

- 미션 생성/참여 흐름
- 위치 업데이트/길안내 흐름
- 도로 상황/상품 확인 흐름
- 귀가 완료 흐름

## 6. 여러 Codex 세션 작업 규칙

1. 각 세션은 하나의 GitHub 이슈만 가져간다.
2. 이슈 본문에 적힌 파일 소유권 밖의 수정은 하지 않는다.
3. 공통 파일 수정이 필요하면 별도 통합 이슈나 최종 머지 세션에서 처리한다.
4. 자신의 작업이 다른 이슈를 막는다면 이슈 댓글에 blocker를 남긴다.
5. 모든 세션은 draft PR 또는 커밋에서 해당 이슈 번호를 `Refs:`로 연결한다.

## 7. 완료 기준

- 핵심 API가 모두 존재하고 역할 토큰 기준으로 접근을 분리한다.
- 부모/아이 핵심 흐름이 통합 테스트 또는 재현 가능한 수동 절차로 검증된다.
- 외부 연동 실패 시 안전한 기본 응답을 반환한다.
- 병렬 작업 세션이 파일 충돌 없이 병행될 수 있다.
