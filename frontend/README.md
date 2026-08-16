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
cp .env.example .env
npm start
```

`EXPO_PUBLIC_API_BASE_URL`에는 backend Function URL을 넣습니다. 아이 참여·상품 확인은 이 URL을 통해 child bearer token과 JPEG multipart만 전송하며 이미지나 token을 기기에 영속화하지 않습니다.

| 명령 | 용도 |
| --- | --- |
| `npm start` | Expo 개발 서버 실행 |
| `npm run android` | Android 앱 실행 |
| `npm run ios` | iOS 앱 실행 |
| `npm run web` | 웹 앱 실행 |
| `npm run lint` | Expo ESLint 검사 |
| `npx tsc --noEmit` | TypeScript 타입 검사 |
| `npm run test:parent-snapshot` | 부모 snapshot cursor·중복 방지 테스트 |

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
