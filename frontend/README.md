# Frontend

Expo Router를 사용하는 React Native 프런트엔드 애플리케이션입니다.

## 기술 스택

| 구분 | 버전 |
| --- | --- |
| Expo | SDK 54 (`~54.0.35`) |
| React | 19.1.0 |
| React Native | 0.81.5 |
| Expo Router | `~6.0.24` |
| TypeScript | `~5.9.2` |

Expo 관련 구현 전에는 SDK 54 기준의 버전별 공식 문서를 확인합니다.

## 실행

저장소 루트에서 다음 명령을 실행합니다.

```bash
cd frontend
npm ci
npm start
```

## 백엔드 연결

미션 생성과 아이 참여는 `EXPO_PUBLIC_API_BASE_URL`의 FastAPI 서버를 호출한다. 로컬 개발에서는 설정하지 않으면 `http://127.0.0.1:8000`을 사용하며, 기기에서 실행할 때는 접근 가능한 개발 서버 주소를 설정한다. 이 값에는 비밀값을 넣지 않는다.

| 명령 | 용도 |
| --- | --- |
| `npm start` | Expo 개발 서버 실행 |
| `npm run android` | Android 앱 실행 |
| `npm run ios` | iOS 앱 실행 |
| `npm run web` | 웹 앱 실행 |
| `npm run lint` | Expo ESLint 검사 |
| `npx tsc --noEmit` | TypeScript 타입 검사 |
| `npm run test:child-mission-state` | 다중 상품 선택·귀가 전환 테스트 |
| `npm run test:location-guidance` | 백엔드 안내 코드·상태 화면 매핑 테스트 |
| `npm run test:safety` | 도로 보수 안내·JPEG 크기 계산 테스트 |
| `npm run test:parent-monitor` | 부모 상태·이벤트 표현 테스트 |
| `npm run test:parent-snapshot` | 부모 snapshot cursor·중복 방지 테스트 |

## 환경 변수

| 이름 | 용도 |
| --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | 백엔드 Function URL. 미션 생성·참여, 아이 위치·JPEG 업로드, 부모 polling에 사용한다. |

아이 화면은 `expo-location`으로 3초 또는 10m 간격의 위치를 전송하고 백엔드 안내 문구를
`expo-speech`로 읽는다. 카메라 화면은 `expo-camera`의 실제 `CameraView`를 사용하며, 도로·상품
JPEG는 1MB 이하만 전송한다. 지원하지 않는 기기·권한 거부·API 오류에서는 횡단 허가를 만들지
않고 보호자와 함께 직접 확인하라는 보수적 안내만 표시한다.

## 디렉터리 구조

| 경로 | 책임 |
| --- | --- |
| `app/` | Expo Router 화면과 라우트 레이아웃 |
| `components/` | 재사용 가능한 UI 컴포넌트 |
| `hooks/` | 공통 React 훅 |
| `constants/` | 테마 등 정적 설정 |
| `assets/` | 이미지와 정적 자산 |
| `scripts/` | 프런트엔드 개발 보조 스크립트 |

## 개발 원칙

- `@/` 별칭은 `frontend/` 루트를 기준으로 사용합니다.
- 서버 비밀값과 핵심 권한 판정 로직을 프런트엔드에 두지 않습니다.
- 백엔드 연동은 문서화된 API 계약을 통해 수행합니다.
- 새 환경 변수는 `.env.example`과 이 문서에 함께 기록합니다.

## 백엔드 연결

부모 모니터는 `EXPO_PUBLIC_API_BASE_URL`의 `GET /missions/{missionId}/snapshot`을 3초마다 호출합니다.
값이 없으면 위치 정보는 요청하지 않고 화면에 재시도 가능한 오류를 표시합니다. 이 값은 공개 앱 설정용 URL이며 비밀값을 넣지 않습니다.
