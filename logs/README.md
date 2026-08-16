# Codex 사용 로그

Codex를 사용한 작업 기록을 사용자별로 보관한다.

## 디렉터리 규칙

GitHub 사용자명을 기준으로 `logs/<name>/` 디렉터리를 만든다.

```text
logs/
├── README.md
└── jhpark324/
    └── README.md
```

개별 로그는 `YYYY-MM-DD-<task-name>.md` 또는 `YYYY-MM-DD-<task-name>.jsonl`
형식을 권장한다.

## 보안 규칙

- API 키, 토큰, 비밀값, 환경 변수 값을 포함하지 않는다.
- 개인정보, 실제 아동의 위치, 원본 이미지를 포함하지 않는다.
- 커밋 전에 로그를 직접 검토하고 민감 정보를 제거한다.
