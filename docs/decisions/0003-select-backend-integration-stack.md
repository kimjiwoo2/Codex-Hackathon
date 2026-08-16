# 0003. 어린이 첫 심부름 도우미 백엔드 연동 스택 선택

- 상태: Accepted
- 결정일: 2026-08-16

## 맥락

데모 시간은 3시간으로 제한되어 있고, 부모/아이 전체 흐름을 모두 다뤄야 한다. 필수 기능에는 길안내, 경로 이탈 감지, 도로 상황 판단, 상품 확인, 부모 polling 조회가 포함된다. 인식률보다 구현 속도를 우선하며, 운영 인프라는 이번 결정 범위에서 제외한다.

## 결정

- 백엔드는 FastAPI 모놀리스를 유지한다.
- 데이터 저장소는 Neon Free Postgres의 AWS Singapore 리전과 pooled SSL 연결을 사용한다.
- 지도/보행 경로는 TMAP Open API를 사용한다.
- 도로 상황 판단과 상품 확인은 OpenAI 비전 API를 사용한다.
- 부모 화면 동기화는 WebSocket 대신 2~3초 polling을 사용한다.
- 배포 기준은 AWS Lambda Python 3.12 + Function URL + Mangum으로 둔다.
- Lambda도 `ap-southeast-1`에 배치해 DB와 리전을 맞춘다.
- 원본 이미지와 장기 위치 이력은 저장하지 않는다.

## 근거

- FastAPI는 현재 저장소 스캐폴드와 일치하고 추가 프레임워크 전환 비용이 없다.
- Neon Postgres는 빠르게 붙일 수 있는 관리형 PostgreSQL이며 SQLAlchemy/psycopg와 바로 연결된다.
- TMAP은 국내 보행 경로와 회전 안내 정보를 제공해 데모 길안내에 적합하다.
- OpenAI 비전 API는 단일 공급자로 도로 상황과 상품 확인을 모두 처리할 수 있다.
- polling은 구현 비용이 낮고 부모 화면 요구를 충족한다.
- Lambda + Function URL은 Python 3.12 런타임을 바로 사용할 수 있고 FastAPI ASGI 앱을 Mangum으로 감쌀 수 있다.

## 결과

- 백엔드 구현은 `services`, `repositories`, `integrations` 경계를 중심으로 나눈다.
- 도로 판단 응답은 안전상 `STOP | CAUTION | UNKNOWN`으로 제한한다.
- `GO`, `CROSS_OK`, 횡단 허가 문구는 schema와 후처리에서 금지한다.
- 실시간 연결보다 HTTP 중심 API 계약과 idempotent 상태 전이에 집중한다.

## 제외한 대안

- App Runner: 신규 고객에게 더 이상 열려 있지 않고 현재 저장소의 Python 3.12 기준과 바로 맞지 않는다.
- AWS Location Service와 Google Maps Routes: 공식 coverage에서 대한민국 보행 경로 요구를 충족하지 못한다.
- Kakao Mobility 도보 길찾기: 제휴 중심 진입 장벽이 있어 해커톤 시연 준비에 불리하다.
- WebSocket 기반 부모 모니터링: 구현 복잡도 대비 이번 시연 이득이 작다.

## 후속 작업

- `TMAP_APP_KEY`, Neon pooled URL, OpenAI 이미지 입력, AWS Lambda 권한을 구현 시작 시 preflight한다.
- Linux Lambda artifact에서 `psycopg`, `openai`, `mangum` import를 검증한다.
- 실제 제품 전환 전 미성년자·위치정보·국외 이전·Zero Data Retention 요구를 별도 검토한다.
