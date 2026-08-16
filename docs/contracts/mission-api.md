# Mission API Contract

> 상태: Proposed<br>
> 기준일: 2026-08-16<br>
> Base URL: `EXPO_PUBLIC_API_BASE_URL`

이 문서는 아이캔 부모·아이 앱과 FastAPI 백엔드 사이의 단일 HTTP 계약이다. 현재 서버에는 `GET /health`만 구현되어 있으며, 제품 API는 이 문서가 합의된 뒤 구현한다.

## 공통 규칙

- JSON 필드는 `camelCase`, 시각은 UTC ISO 8601 문자열을 사용한다.
- 인증 요청은 `Authorization: Bearer <roleToken>`을 사용한다.
- 참여 코드는 숫자 6자리이며 생성 후 30분 동안 유효하고 최초 참여 시 소진된다.
- 부모 토큰은 부모 API, 아이 토큰은 아이 API에만 사용할 수 있다.
- 토큰 원문과 참여 코드는 로그에 남기지 않는다.
- 정상 네트워크에서 임무 조회는 2초 폴링을 허용한다.
- `PATCH /location`은 최대 3초에 한 번 또는 10m 이상 이동했을 때 호출한다.

## 공통 타입

```ts
type MissionStatus =
  | "WAITING"
  | "GOING"
  | "SHOPPING"
  | "RETURNING"
  | "COMPLETED"
  | "CANCELED";

type Role = "PARENT" | "CHILD";
type LocationSource = "GPS" | "DEMO";
type VerificationResult = "MATCH" | "NO_MATCH" | "UNSURE";

interface Coordinate {
  latitude: number;
  longitude: number;
}

interface MissionLocation extends Coordinate {
  accuracyMeters: number;
  headingDegrees: number | null;
  recordedAt: string;
  source: LocationSource;
}

interface MissionItem {
  id: string;
  name: string;
  brand: string | null;
  quantity: number;
  unit: string | null;
  referenceImageUrl: string | null;
  verified: boolean;
}

interface NavigationState {
  offRoute: boolean;
  offRouteDetectedAt: string | null;
}

interface MissionSnapshot {
  id: string;
  status: MissionStatus;
  destination: { name: string; coordinate: Coordinate };
  returnPoint: { name: string; coordinate: Coordinate };
  items: MissionItem[];
  settings: {
    shareLocation: boolean;
    notifyOffRoute: boolean;
  };
  latestChildLocation: MissionLocation | null;
  navigation: NavigationState;
  joinedAt: string | null;
  updatedAt: string;
}
```

## 설정 동작

- `shareLocation: true`: 아이 앱이 최신 위치를 서버로 보내고 부모의 `MissionSnapshot.latestChildLocation`에 노출한다.
- `shareLocation: false`: 실제 GPS는 아이 기기의 길안내에만 사용한다. 아이 앱은 위치 API를 호출하지 않고 서버는 `latestChildLocation: null`을 반환한다.
- `notifyOffRoute: true`: 아이 앱이 위치 요청에 `isOffRoute`를 포함한다. 서버는 `navigation`에 최신 이탈 상태를 반영하고 부모 앱은 2초 폴링으로 인앱 경고를 표시한다. 운영체제 푸시 알림은 MVP 범위가 아니다.
- `notifyOffRoute: false`: 아이의 로컬 경로 이탈 음성은 유지하지만 서버는 `navigation.offRoute: false`, `offRouteDetectedAt: null`을 반환한다.
- `notifyOffRoute: true`는 `shareLocation: true`일 때만 허용한다. 그렇지 않으면 임무 생성 요청을 `VALIDATION_ERROR`로 거부한다.

## 상태 전이

| 현재 | 다음 | 호출 주체 | 조건 |
| --- | --- | --- | --- |
| `WAITING` | `GOING` | 서버 | 아이가 코드로 최초 참여 |
| `GOING` | `SHOPPING` | 아이 | 마트 도착 체크포인트 확인 |
| `SHOPPING` | `RETURNING` | 아이 | 모든 상품 확인 |
| `RETURNING` | `COMPLETED` | 아이 | 귀가 체크포인트 확인 |
| 비종료 상태 | `CANCELED` | 부모 | 부모가 임무 취소 |

종료 상태에서는 상태·위치·상품 판별 변경을 거부한다. 허용되지 않은 전이는 `MISSION_STATUS_CONFLICT`를 반환한다.

## 엔드포인트

### `GET /health`

인증 없이 서버 가용성을 확인한다.

```json
{ "status": "ok" }
```

### `POST /missions`

부모가 임무를 생성한다.

```json
{
  "destination": {
    "name": "행복슈퍼",
    "coordinate": { "latitude": 37.5665, "longitude": 126.978 }
  },
  "returnPoint": {
    "name": "우리 집",
    "coordinate": { "latitude": 37.5658, "longitude": 126.9772 }
  },
  "items": [
    { "name": "우유", "brand": null, "quantity": 1, "unit": "개", "referenceImageUrl": null }
  ],
  "settings": { "shareLocation": true, "notifyOffRoute": true }
}
```

`201 Created`

```json
{
  "mission": {
    "id": "mission_uuid",
    "status": "WAITING",
    "destination": {
      "name": "행복슈퍼",
      "coordinate": { "latitude": 37.5665, "longitude": 126.978 }
    },
    "returnPoint": {
      "name": "우리 집",
      "coordinate": { "latitude": 37.5658, "longitude": 126.9772 }
    },
    "items": [
      {
        "id": "item_uuid",
        "name": "우유",
        "brand": null,
        "quantity": 1,
        "unit": "개",
        "referenceImageUrl": null,
        "verified": false
      }
    ],
    "settings": { "shareLocation": true, "notifyOffRoute": true },
    "latestChildLocation": null,
    "navigation": { "offRoute": false, "offRouteDetectedAt": null },
    "joinedAt": null,
    "updatedAt": "2026-08-16T05:00:00Z"
  },
  "joinCode": "482913",
  "joinCodeExpiresAt": "2026-08-16T05:30:00Z",
  "parentToken": "opaque_parent_token"
}
```

### `POST /missions/join`

```json
{ "joinCode": "482913" }
```

`200 OK`

```json
{
  "mission": {
    "id": "mission_uuid",
    "status": "GOING",
    "destination": {
      "name": "행복슈퍼",
      "coordinate": { "latitude": 37.5665, "longitude": 126.978 }
    },
    "returnPoint": {
      "name": "우리 집",
      "coordinate": { "latitude": 37.5658, "longitude": 126.9772 }
    },
    "items": [
      {
        "id": "item_uuid",
        "name": "우유",
        "brand": null,
        "quantity": 1,
        "unit": "개",
        "referenceImageUrl": null,
        "verified": false
      }
    ],
    "settings": { "shareLocation": true, "notifyOffRoute": true },
    "latestChildLocation": null,
    "navigation": { "offRoute": false, "offRouteDetectedAt": null },
    "joinedAt": "2026-08-16T05:03:00Z",
    "updatedAt": "2026-08-16T05:03:00Z"
  },
  "childToken": "opaque_child_token"
}
```

코드가 틀리거나 만료·소진되면 각각 `JOIN_CODE_INVALID`, `JOIN_CODE_EXPIRED`, `JOIN_CODE_USED`를 반환한다.

### `GET /missions/{missionId}`

부모 또는 아이 토큰으로 `MissionSnapshot`을 조회한다. `200 OK`와 함께 전체 스냅샷을 반환한다.

### `PATCH /missions/{missionId}/location`

아이 토큰만 사용할 수 있다.

```json
{
  "latitude": 37.5661,
  "longitude": 126.9776,
  "accuracyMeters": 8.2,
  "headingDegrees": 92.0,
  "recordedAt": "2026-08-16T05:04:00Z",
  "source": "GPS",
  "isOffRoute": false
}
```

`200 OK`로 저장된 `MissionLocation`을 반환한다. 서버가 보유하는 값보다 오래된 `recordedAt`은 `STALE_LOCATION`으로 거부한다. `shareLocation`이 꺼진 임무에서는 위치 요청을 `LOCATION_SHARING_DISABLED`로 거부한다.

### `PATCH /missions/{missionId}/status`

```json
{ "status": "SHOPPING" }
```

아이 토큰으로 정상 전이를 요청한다. `200 OK`로 갱신된 `MissionSnapshot`을 반환한다.

### `POST /missions/{missionId}/items/{itemId}/verify`

아이 토큰으로 `multipart/form-data`의 `image` 필드를 업로드한다. JPEG 또는 PNG, 최대 5MB만 허용한다.

`200 OK`

```json
{
  "result": "MATCH",
  "observedProduct": "서울우유 1L",
  "reason": "요청한 우유 품목과 종류가 일치합니다.",
  "childMessage": "찾았다! 부탁한 우유가 맞아."
}
```

- `UNSURE`는 성공으로 간주하지 않고 재촬영을 요청한다.
- 얼굴이 감지되면 OpenAI를 호출하지 않고 `FACE_DETECTED`를 반환한다.
- 원본 사진은 영구 저장하지 않고 요청 종료 시 폐기한다.

### `POST /missions/{missionId}/cancel`

부모 토큰만 사용할 수 있다. `200 OK`로 `CANCELED` 상태의 `MissionSnapshot`을 반환한다.

## 오류 계약

모든 오류는 다음 형태를 사용한다.

```json
{
  "code": "JOIN_CODE_EXPIRED",
  "message": "참여 코드가 만료되었습니다.",
  "retryable": false
}
```

| HTTP | 대표 코드 | 의미 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR`, `FACE_DETECTED` | 요청 형식 또는 사진이 부적합함 |
| 401 | `AUTH_REQUIRED`, `TOKEN_INVALID` | 인증이 없거나 유효하지 않음 |
| 403 | `ROLE_FORBIDDEN` | 역할 권한이 없음 |
| 404 | `MISSION_NOT_FOUND`, `ITEM_NOT_FOUND` | 대상을 찾을 수 없음 |
| 409 | `JOIN_CODE_USED`, `MISSION_STATUS_CONFLICT`, `STALE_LOCATION`, `LOCATION_SHARING_DISABLED` | 현재 상태와 요청이 충돌함 |
| 410 | `JOIN_CODE_EXPIRED` | 참여 코드가 만료됨 |
| 413 | `IMAGE_TOO_LARGE` | 사진 용량 제한 초과 |
| 422 | `JOIN_CODE_INVALID` | 입력값은 형식상 유효하지만 처리할 수 없음 |
| 503 | `AI_UNAVAILABLE` | 상품 판별 서비스를 일시적으로 사용할 수 없음 |

## 데이터 수명과 보안

- 백엔드는 원문 역할 토큰을 해시하여 비교한다.
- 최신 위치만 보유하며 위치 이력을 만들지 않는다.
- `COMPLETED` 또는 `CANCELED` 이후 1시간 안에 임무와 위치를 삭제한다.
- 삭제된 임무를 다시 조회하면 `MISSION_NOT_FOUND`를 반환하며 별도의 임무 만료 오류는 사용하지 않는다.
- 데모용 인메모리 저장소이므로 서버 재시작 시 모든 임무, 참여 코드, 역할 토큰이 즉시 소실된다.
- OpenAI API 키는 백엔드 환경 변수로만 관리한다.
- 위치, 참여 코드, 역할 토큰은 OpenAI 요청에 포함하지 않는다.
- 해커톤 데모에서는 실제 아동 개인정보를 사용하지 않는다.
