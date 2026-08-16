# Product Spec

> 상태: Ready for implementation<br>
> 오너: 개발팀<br>
> 최종 갱신: 2026-08-16

## 1. 문제

첫 심부름을 하는 아이는 지도 화면을 계속 해석하기 어렵고, 부모는 아이의 위치와 진행 상황을 확인하고 싶다. 서비스는 부모가 지정한 마트와 상품을 기준으로 출발부터 귀가까지 아이에게 한 번에 하나씩 음성 행동을 안내하고, 부모에게 현재 위치·상태·주의 이벤트를 보여준다.

## 2. 목표

3시간 개발 종료 시 다음 경로를 통제된 데모에서 끝까지 시연한다.

`부모 미션 생성 → 아이 코드 참여 → 마트행 안내 → 주변 위험 보조 경고 → 상품 확인 → 귀가 안내 → 완료 → 부모 확인`

가장 중요한 완료 조건은 아이 앱이 백엔드 응답을 TTS로 읽어 마트행과 귀가에서 다음 행동을 안내할 수 있는 것이다.

## 3. 비목표

- 부모 앱이 닫힌 상태의 push 알림
- WebSocket, Redis, queue, 다중 서버, 고가용성
- 연속 원본 영상 전송·저장과 장기 위치 이력
- 자동 재탐색, 정밀 map matching, 높은 비전 인식률 튜닝
- 운영 모니터링, 무중단 배포, 재해 복구
- 실제 아이가 혼자 의존할 수 있는 안전 제품 출시와 정식 컴플라이언스 완료
- AI의 “건너도 된다” 판단 또는 안전 보장

## 4. 대상 사용자와 핵심 시나리오

| 사용자 | 상황 | 기대 결과 |
| --- | --- | --- |
| 부모 | 집·마트 좌표와 상품을 등록 | `missionId`, 6자리 `joinCode`, `parentToken` 수신 |
| 아이 | 코드로 참여하고 이동 | `childToken` 수신 후 2~3초 위치 업데이트마다 음성 안내 수신 |
| 아이 | 카메라로 도로 상황을 비춤 | `STOP | CAUTION | UNKNOWN` 중 하나와 고정 안전 문구 수신 |
| 아이 | 마트에서 상품을 비춤 | `MATCH | SIMILAR | MISMATCH | UNKNOWN` 판정 수신 |
| 부모 | 앱을 열고 진행 상황 확인 | 3초 polling으로 최신 위치·상태·상품·신규 이벤트 확인 |
| 아이 | 상품을 못 찾았거나 귀가 필요 | 상품 상태와 무관하게 귀가 모드 시작 |

## 5. 기능 요구사항

- [ ] P0: 부모가 집·마트 좌표와 상품 목록으로 미션 생성
- [ ] P0: 아이가 6자리 코드로 참여하고 역할별 token 발급
- [ ] P0: 상태 `WAITING → GOING → SHOPPING → RETURNING → COMPLETED`
- [ ] P0: TMAP 왕복 보행 경로를 이용한 좌·우회전·횡단보도·도착 안내
- [ ] P0: GPS 정확도, heading, progress를 이용한 역방향·경로 이탈 안내
- [ ] P0: 샘플 JPEG 기반 도로 상황 보조 판단과 부모 위험 이벤트
- [ ] P0: 상품 이미지와 이름·브랜드·용량 비교 결과 저장
- [ ] P0: 상품 결과와 관계없이 귀가 명령 가능
- [ ] P0: 부모 snapshot polling으로 최신 위치·상태·상품·이벤트 제공
- [ ] P0: 외부 AI 실패 시 보수적 안내로 안전하게 저하
- [ ] P1: 장시간 정지·위치 미수신을 snapshot 시점에 계산해 부모에게 표시

## 6. 안전·비기능 요구사항

- 도로 AI의 허용 결과는 `STOP | CAUTION | UNKNOWN`뿐이다.
- `GO`, `CROSS_OK`, “건너도 된다”와 동등한 판단은 schema와 후처리에서 금지한다.
- TMAP이 횡단보도 step을 나타내면 AI 결과와 무관하게 정지 안내를 우선한다.
- 도로 요청은 `capturedAt`을 포함해야 한다. 서버 시각보다 10초 넘게 오래되었거나 5초 넘게 미래인 프레임은 OpenAI를 호출하지 않고 `UNKNOWN`과 직접 확인 안내로 변환한다.
- OpenAI 오류·timeout은 `UNKNOWN`과 직접 확인 안내로 변환한다.
- 미션별 도로 비전은 DB의 10초 lease로 한 요청만 처리하고 겹친 프레임은 폐기한다.
- 원본 영상·상품 이미지·Base64·평문 token을 DB나 로그에 저장하지 않는다.
- 아이 위치 update와 부모 snapshot의 정상 데모 간격은 각각 2~3초, 3초다.
- 외부 API 호출은 backend adapter 안에서만 수행하고 timeout을 둔다.
- 비밀값은 환경 변수로만 주입하고 저장소에 커밋하지 않는다.
- 시연은 보호자 동행과 식별정보가 없는 통제 이미지로 제한한다.

## 7. API 및 데이터 계약

필수 API:

```text
POST /missions
POST /missions/join
POST /missions/{missionId}/locations
POST /missions/{missionId}/vision/road
POST /missions/{missionId}/items/{itemId}/verify
POST /missions/{missionId}/commands/return-home
GET  /missions/{missionId}/snapshot?afterEventId={cursor}
```

데이터는 `missions`, `mission_items`, `mission_events` 세 테이블로 제한한다. 세부 schema, 파일 소유권, 테스트 기준은 [`backend-parallel-implementation-plan.md`](backend-parallel-implementation-plan.md)를 따른다.

## 8. 완료 조건

- [ ] P0 사용자 시나리오가 한 HTTP E2E 테스트에서 처음부터 끝까지 동작한다.
- [ ] TMAP/OpenAI mock 기반 단위·통합 테스트가 통과한다.
- [ ] 실제 AWS Function URL에서 health와 외부 연동 smoke가 통과한다. 자격 증명·키가 없으면 mock E2E 완료와 `SMOKE_BLOCKED_BY_ENV`를 분리해 기록한다.
- [ ] 역방향·이탈·안전 귀가·event cursor 규칙이 자동화 테스트로 보호된다.
- [ ] `CROSS_OK` 또는 횡단 허가 결과가 존재하지 않음을 자동화 테스트로 증명한다.
- [ ] DB와 로그에 원본 이미지와 평문 token이 없음을 검증한다.
- [ ] `uv run ruff format --check .`, `uv run ruff check .`, `uv run pytest`가 통과한다.
- [ ] 미완료 범위와 실제 아이 단독 사용 불가 제약을 문서화한다.

## 9. 구현 전 확인 사항

- `TMAP_APP_KEY`가 실제 보행 경로 요청에 성공해야 한다. 현재 미확인 상태다.
- `DATABASE_URL`이 Neon pooled SSL endpoint인지 확인해야 한다.
- OpenAI 이미지 입력 실호출과 계정의 `OPENAI_VISION_MODEL` 접근 권한을 확인해야 한다.
- AWS 계정에 Lambda, IAM role, Function URL을 만들 권한이 있어야 한다.
