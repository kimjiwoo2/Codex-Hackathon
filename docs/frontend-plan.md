# Frontend Implementation Plan — 아이캔(iCan)

> 상태: Proposed<br>
> 대상: Expo SDK 54 / iPhone Expo Go 우선<br>
> 구현 시작 조건: 문서 PR 병합 및 필수 Figma 화면 완성

## 화면과 라우팅

Expo Router의 Stack을 기본으로 사용하고 부모·아이 흐름을 경로로 분리한다.

```text
app/
├── index.tsx                  # 역할 선택 또는 진행 중 임무 복구
├── parent/
│   ├── index.tsx             # 부모 홈
│   ├── create/
│   │   ├── destination.tsx   # 목적지 선택
│   │   ├── items.tsx         # 물건 선택
│   │   └── confirm.tsx       # 경로·물건·설정 확인
│   ├── code.tsx              # 참여 코드 표시
│   └── monitor.tsx           # 아이 위치와 상태 모니터링
└── child/
    ├── join.tsx              # 참여 코드 입력
    ├── confirm.tsx           # 심부름 확인
    └── mission.tsx           # 이동·상품·귀가·완료 상태 화면
```

진행 중 역할과 임무 토큰이 SecureStore에 있으면 앱 시작 시 해당 흐름을 복구한다. 종료된 임무는 로컬 세션을 지우고 역할 선택으로 돌아간다.

## Figma 매핑과 디자인 시스템

| Figma | 앱 화면 | 상태 |
| --- | --- | --- |
| `4:2469` 메인 화면 | 부모 홈 | 완성 |
| `4:2890` 심부름 만들기 1 | 목적지 선택 | 완성 |
| `4:3418` 심부름 만들기 2 | 물건 선택 | 완성 |
| `4:3651` 심부름 만들기 3 | 확인 및 생성 | 완성 |
| 역할 선택 | 앱 시작 | 디자인 대기 |
| 참여 코드·부모 모니터링 | 부모 흐름 | 디자인 대기 |
| 아이 코드 입력·임무 진행 | 아이 흐름 | 디자인 대기 |

- 기준 프레임은 402×874이고 Pretendard를 사용한다.
- 핵심 토큰은 본문 `#141517`, 흰색 `#FFFFFF`, 경계 `#E6E7E9`, 노랑 `#FFD66C`, 초록 `#A3B755`, 연두 `#E0EBB0`, 배경 `#FAF7F1`이다.
- 공통 Header, PrimaryButton, Card, TextField, StatusBadge, Empty/Error State를 먼저 만든다.
- Figma 임시 URL을 런타임에 참조하지 않고 승인된 원본 에셋을 `frontend/assets/ican/`에 저장한다.
- 앱 표시명은 `아이캔`, slug와 scheme은 `ican`으로 설정한다.

## 상태 관리와 API

- 서버 상태는 TanStack Query로 관리하고 진행 중 임무를 2초마다 폴링한다.
- 생성·참여·위치·상태·판별 요청은 문서화된 API 클라이언트 한 곳을 통과한다.
- API 주소는 `EXPO_PUBLIC_API_BASE_URL`에서 읽는다.
- 부모·아이 토큰과 활성 임무 ID는 Expo SecureStore에 저장한다.
- 화면 전용 입력 상태는 지역 상태로 유지하고 서버 스냅샷을 중복 복사하지 않는다.
- 백엔드가 준비되기 전에는 동일 인터페이스의 mock adapter를 사용하되 최종 데모는 실제 API로 검증한다.

## GPS와 데모 경로

- `expo-location`의 전경 위치 구독만 사용한다.
- 첫 유효 GPS 좌표를 원점으로 삼아 상대 오프셋의 데모 경로와 체크포인트를 생성한다.
- 정확도가 50m보다 나쁜 좌표는 경로 판정에 사용하지 않는다.
- 위치는 3초 간격 또는 10m 이상 이동 시 전송한다.
- 경로선에서 25m 이상 벗어난 상태가 3회 연속 확인되면 경로 이탈로 판정한다.
- 체크포인트 반경 15m 안에 진입하면 다음 안내로 전환한다.
- 숨은 데모 조작은 화면의 버전 영역을 5회 탭해 열고 다음 체크포인트, 이탈, 마트 도착, 귀가 완료를 제공한다.
- 데모 조작도 GPS 이벤트와 동일한 mission reducer를 사용하고 전송 위치의 `source`만 `DEMO`로 표시한다.

## 음성·안전 안내

- `expo-speech`로 한국어 문구를 재생하고 최근 안내를 다시 듣는 버튼을 제공한다.
- 같은 안내는 10초 안에 자동 반복하지 않는다.
- 새 안전 안내가 발생하면 이전 음성을 중지하고 최신 안내를 재생한다.
- 횡단보도 문구는 `횡단보도 앞이야. 멈추고 신호와 주변을 직접 확인하자.`로 고정한다.
- `건너도 돼`, `안전해`처럼 횡단 가능을 보장하는 문구는 사용하지 않는다.
- 임무 중 `expo-keep-awake`로 화면 꺼짐을 방지한다.
- iOS 무음 모드에서는 소리가 나지 않을 수 있음을 데모 체크리스트에 포함한다.

## 상품 카메라

- `expo-camera`의 후면 카메라를 상품 확인 시에만 마운트한다.
- 상품이 프레임을 채우고 사람이 나오지 않도록 촬영 가이드를 표시한다.
- JPEG 한 장을 최대 5MB로 업로드하며 처리 중 추가 촬영을 막는다.
- `MATCH`는 상품 완료, `NO_MATCH`는 다른 상품 안내, `UNSURE`는 재촬영 안내로 처리한다.
- 카메라 권한 거부, 얼굴 감지, 네트워크 실패, AI 일시 오류에 별도 복구 UI를 제공한다.

## 구현 순서

1. Expo 앱 이름, Router Stack, 디자인 토큰과 공통 UI
2. 타입, API client, SecureStore 세션, mock adapter
3. 부모 생성 3단계와 참여 코드
4. 아이 코드 참여와 임무 상태 reducer
5. 지도, GPS, 경로 이탈, 데모 조작
6. 음성 안내와 안전 문구
7. 상품 카메라와 판별 결과
8. 부모 모니터링, 귀가, 완료·취소
9. 실제 백엔드 연결과 두 기기 검증

## 테스트와 수동 검증

- 단위 테스트: 참여 코드 형식, 상태 전이, GPS 정확도 필터, 경로 이탈 연속 판정, 음성 중복 방지, API 오류 매핑
- 통합 테스트: 생성→참여→위치→상품 판별→귀가→완료, 만료·소진 코드, 네트워크 재연결
- 정적 검증: `npm run lint`, `npx tsc --noEmit`, `npx expo-doctor`
- 시각 검증: iPhone 402×874 캡처를 Figma와 비교
- 두 기기 검증: 아이 위치·상태가 부모 화면에 5초 이내 반영되는지 확인
- 실패 검증: 위치·카메라 권한 거부, GPS 품질 저하, OpenAI 지연, `UNSURE`, 얼굴 감지

## 알려진 제약

- Expo Go 전경에서만 위치 업데이트를 기대한다.
- 실제 장소 검색과 도보 경로는 제공하지 않는다.
- 웹은 지도·카메라 핵심 완료 기준에 포함하지 않는다.
- 실제 아동 개인정보를 사용한 운영 검증은 범위에서 제외한다.

## 공식 참고 자료

- [Expo Location](https://docs.expo.dev/versions/v54.0.0/sdk/location/)
- [Expo Camera](https://docs.expo.dev/versions/v54.0.0/sdk/camera/)
- [Expo Speech](https://docs.expo.dev/versions/v54.0.0/sdk/speech/)
- [react-native-maps](https://docs.expo.dev/versions/v54.0.0/sdk/map-view/)
- [OpenAI Under 18 API Guidance](https://developers.openai.com/api/docs/guides/safety-checks/under-18-api-guidance)
