# 0004. 2초 폴링 기반 임무 동기화

- 상태: Accepted
- 결정일: 2026-08-16
- 결정자: iCan 해커톤 팀

## Context

부모와 아이 앱은 임무 상태와 최신 위치를 몇 초 안에 공유해야 한다. WebSocket은 빠르지만 연결 관리, 재연결, 배포 구성이 해커톤 MVP에 추가 부담을 만든다.

## Decision

진행 중 임무를 2초 간격의 HTTP 폴링으로 동기화한다. 아이 위치는 최대 3초 간격 또는 10m 이상 이동했을 때 별도 PATCH 요청으로 전송한다. 최종 데모에서 부모 화면 반영 목표는 5초 이내다.

## Alternatives considered

- WebSocket — 실시간성은 좋지만 구현과 운영 복잡도가 높다.
- Server-Sent Events — 서버→클라이언트에는 적합하지만 아이 위치 업로드에는 별도 요청이 필요하다.

## Consequences

### Positive

- 기존 FastAPI HTTP 구조와 TanStack Query만으로 구현할 수 있다.
- 네트워크 재연결과 오류 처리가 단순하다.

### Negative / Trade-offs

- 요청 수가 증가하고 최대 수 초의 지연이 생긴다.
- 앱이 백그라운드로 가면 동기화가 중단될 수 있다.

## Follow-up

- [ ] 백엔드가 데모 동시 접속량에서 폴링을 처리하는지 확인한다.
- [ ] 운영 전환 시 WebSocket 또는 푸시 방식의 필요성을 재평가한다.
