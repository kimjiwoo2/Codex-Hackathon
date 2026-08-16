# Git 및 GitHub 컨벤션

## 브랜치

`<type>/<short-kebab-description>` 형식을 사용한다.

| Type | 용도 | 예시 |
| --- | --- | --- |
| `feat` | 기능 개발 | `feat/user-login` |
| `fix` | 버그 수정 | `fix/token-refresh` |
| `docs` | 문서 변경 | `docs/api-contract` |
| `refactor` | 동작 변경 없는 구조 개선 | `refactor/auth-service` |
| `test` | 테스트 추가·수정 | `test/login-flow` |
| `chore` | 도구, 설정, 유지보수 | `chore/ci-setup` |

- `main`에서 짧게 분기하고, 하나의 목적만 담는다.
- 작업 중 최신 `main`을 반영하되 공유 브랜치의 히스토리는 임의로 재작성하지 않는다.
- 머지 후 브랜치는 삭제한다.

## 커밋

커밋 메시지는 아래 형식을 사용한다. `type`과 `scope`는 영문 소문자로 쓰고,
제목과 본문은 한글로 작성한다.

```text
<type>(선택 scope): <한글 명사형 작업 요약>

[선택 본문: 변경 이유와 제약을 한글로 설명]

[선택 footer]
```

예시:

```text
feat(auth): 이메일 로그인 API 추가

비밀번호 인증과 소셜 로그인을 분리해 인증 실패 원인을 명확히 한다.

fix(frontend): 폼 중복 제출 방지
docs: 데이터베이스 선택 근거 기록
```

규칙:

- 허용 type: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`, `revert`.
- 제목과 본문은 한글로 작성한다. 고유명사, 코드 식별자, 명령어는 원문 표기를 허용한다.
- 제목은 서술형 문장이 아닌 명사형 작업 요약으로 작성하고 마침표를 붙이지 않는다.
- 논리적으로 독립적인 변경은 별도 커밋으로 나눈다.
- 호환성을 깨는 변경은 `!`와 `BREAKING CHANGE:` footer로 명시한다.
- 이슈 연결은 footer에 `Refs: #123`, 자동 종료는 `Closes: #123`으로 적는다.

## Pull Request

- 제목은 커밋 메시지와 동일한 `<type>(선택 scope): <한글 명사형 작업 요약>` 형식을 사용한다.
- 제목과 본문은 한글로 작성한다. 고유명사, 코드 식별자, 명령어는 원문 표기를 허용한다.
- 예시: `docs: 개발 기준 구성`
- Squash merge 시 PR 제목이 최종 커밋 제목이 되므로 머지 전에 다시 확인한다.
- PR 하나는 하나의 목표를 해결하며 리뷰 가능한 크기로 유지한다.
- Draft PR은 이른 공유에 사용하고, 완료 조건을 충족하면 Ready for review로 전환한다.
- 설명에는 문제, 변경 내용, 검증 결과, 영향과 위험, 관련 문서·이슈를 포함한다.
- 작성자는 셀프 리뷰를 완료하고 불필요한 디버그 코드와 비밀값이 없는지 확인한다.
- 리뷰 의견은 해결하거나 근거를 남긴 뒤 resolve한다.
- 기본 머지 방식은 Squash and merge로 하며, CI 통과와 승인 후 머지한다.

상세 작성 양식은 [`.github/pull_request_template.md`](../../.github/pull_request_template.md)를 따른다.
