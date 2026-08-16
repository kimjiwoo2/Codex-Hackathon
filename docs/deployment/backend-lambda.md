# Backend Lambda 배포

> 범위: BE-09 W1 패키징 경계와 BE-10 W5 Function URL smoke 인계
>
> 리전·런타임·아키텍처: `ap-southeast-1`, Python 3.12, x86_64

## 구현 상태

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| Mangum handler | W1 완료 | `app.lambda_handler.handler` |
| Linux x86_64 zip build | W1 완료 | `backend/deploy/build_lambda_zip.sh` |
| handler Function URL event smoke | W1 완료 | `backend/tests/unit/test_lambda_handler.py` |
| Linux artifact import smoke | W1 자동화 완료 | Linux x86_64 또는 Lambda 컨테이너에서 `smoke_lambda_zip.sh` 실행 |
| 실제 Function URL `/health` | W5 인계 | BE-10 통합 후 AWS 자격 증명과 실행 role로 검증 |

API Gateway, VPC, CloudFormation 전면 구축, 운영 모니터링은 이 범위에 포함하지 않는다.

## 패키지 빌드

저장소에 설치된 `uv`와 `backend/uv.lock`을 사용한다.

```bash
cd backend
./deploy/build_lambda_zip.sh
```

기본 산출물은 Git에서 제외되는 `backend/dist/backend-lambda.zip`이다. 다른 경로가 필요하면 첫 번째 인자로 전달한다.

```bash
./deploy/build_lambda_zip.sh /tmp/backend-lambda.zip
```

빌드는 잠금 파일의 production dependency만 export하고 CPython 3.12용 `x86_64-manylinux_2_28` wheel만 설치한다. Python 3.12 Lambda는 Amazon Linux 2023과 glibc 2.34를 사용하므로 이 wheel 기준과 호환된다. 애플리케이션과 dependency는 zip 루트에 배치하며, handler는 `app.lambda_handler.handler`다.

빌드 마지막 단계는 다음을 자동 검증한다.

- `app`, `mangum`, `openai`, `psycopg` package가 zip 루트에 존재
- `psycopg[binary]`의 CPython 3.12 x86_64 Linux extension 존재
- zip 경로에 절대 경로나 `..` 없음
- 직접 업로드용 zip 50 MiB 이하, 압축 해제 내용 250 MiB 이하

AWS 참고 문서:

- [Python zip 패키징](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [Python 3.12 런타임과 Amazon Linux 2023](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Lambda package quota](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)

### 재현 가능성 확인

동일한 source ref와 `uv.lock`에서 두 번 만든 artifact의 SHA-256이 같아야 한다.

```bash
./deploy/build_lambda_zip.sh /tmp/backend-lambda-a.zip
./deploy/build_lambda_zip.sh /tmp/backend-lambda-b.zip
shasum -a 256 /tmp/backend-lambda-a.zip /tmp/backend-lambda-b.zip
```

## smoke

### 로컬 handler smoke

네트워크와 AWS 자격 증명 없이 Function URL payload가 FastAPI `/health`까지 전달되는지 확인한다.

```bash
cd backend
uv run pytest tests/unit/test_lambda_handler.py -q
```

### Linux artifact import smoke

Linux x86_64 + Python 3.12 호스트에서는 직접, 다른 호스트에서는 Docker의 공식 Lambda Python 3.12 image로 실행한다.

```bash
cd backend
./deploy/smoke_lambda_zip.sh
```

성공 결과에는 다음 두 줄이 포함된다.

```text
LAMBDA_IMPORT_SMOKE=ok
HANDLER_TYPE=Mangum
```

Linux x86_64 Python 3.12와 Docker가 모두 없으면 스크립트는 exit 2와 `SMOKE_BLOCKED_BY_ENV`를 반환한다. 이는 artifact 구조 검증 실패가 아니라 native Linux import 실행 환경 부재를 뜻한다.

## 환경 변수 계약

값은 저장소, issue, PR, shell history에 기록하지 않는다. W5 배포 담당자는 저장소 밖의 권한 `0600` JSON 파일이나 승인된 secret 주입 경로를 사용한다.

필수 이름:

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `TMAP_APP_KEY`

선택 이름:

- `APP_ENV`
- `CORS_ALLOW_ORIGINS`
- `DATABASE_URL_DIRECT`
- `LOCATION_EVENT_COOLDOWN_SECONDS`
- `LOCATION_OFF_ROUTE_METERS`
- `LOCATION_WRONG_WAY_DEGREES`
- `MISSION_JOIN_CODE_TTL_MINUTES`
- `OPENAI_VISION_MODEL`

AWS CLI에는 값이 들어 있는 저장소 밖 파일만 전달한다.

```bash
LAMBDA_ENV_FILE=/absolute/path/outside-repository/lambda-environment.json
aws lambda update-function-configuration \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --environment "file://${LAMBDA_ENV_FILE}"
aws lambda wait function-updated \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}"
```

## Function URL 배포

아래 명령은 새 운영 인프라를 만들기 위한 템플릿이 아니라, 해커톤 데모용 Lambda 한 개와 Function URL 경계를 검증하기 위한 최소 절차다. 이미 승인된 Lambda execution role을 사용한다.

```bash
export AWS_REGION=ap-southeast-1
export FUNCTION_NAME=first-errand-backend
: "${LAMBDA_ROLE_ARN:?승인된 Lambda execution role ARN을 먼저 export하세요}"
: "${FRONTEND_ORIGIN:?통제된 데모 frontend origin을 먼저 export하세요}"

cd backend
./deploy/build_lambda_zip.sh

aws lambda create-function \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --runtime python3.12 \
  --architectures x86_64 \
  --handler app.lambda_handler.handler \
  --role "${LAMBDA_ROLE_ARN}" \
  --timeout 30 \
  --memory-size 1024 \
  --zip-file fileb://dist/backend-lambda.zip
```

함수가 이미 있으면 `create-function` 대신 code만 갱신한다.

```bash
aws lambda update-function-code \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --zip-file fileb://dist/backend-lambda.zip
aws lambda wait function-updated \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}"
```

Expo demo client는 SigV4를 사용하지 않으므로 Function URL은 `NONE` auth를 사용하고 애플리케이션의 역할별 bearer token으로 mission API를 보호한다. `NONE`은 URL을 아는 누구나 Lambda를 호출할 수 있다는 뜻이므로 통제된 데모에만 사용한다.

```bash
aws lambda create-function-url-config \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --auth-type NONE \
  --cors "{\"AllowOrigins\":[\"${FRONTEND_ORIGIN}\"],\"AllowMethods\":[\"GET\",\"POST\",\"OPTIONS\"],\"AllowHeaders\":[\"authorization\",\"content-type\"],\"MaxAge\":300}"

aws lambda add-permission \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal '*' \
  --function-url-auth-type NONE

aws lambda add-permission \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --statement-id FunctionURLInvokeAllowPublicAccess \
  --action lambda:InvokeFunction \
  --principal '*' \
  --invoked-via-function-url
```

AWS CLI로 `NONE` URL을 만들 때는 `lambda:InvokeFunctionUrl`과 `lambda:InvokeFunction` resource policy를 각각 추가해야 한다. 자세한 정책 조건은 [Function URL access control](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)을 따른다.

### `/health` 확인

```bash
FUNCTION_URL="$(aws lambda get-function-url-config \
  --region "${AWS_REGION}" \
  --function-name "${FUNCTION_NAME}" \
  --query FunctionUrl \
  --output text)"

curl --fail --silent --show-error "${FUNCTION_URL}health"
```

기대 응답:

```json
{"status":"ok"}
```

## W5 인계 체크리스트

BE-10 통합 담당자는 다음을 완료하고 issue/PR에 실제 결과를 기록한다.

- 모든 feature router가 기준 ref에 통합된 뒤 exact commit에서 artifact 재빌드
- Linux artifact import smoke 성공
- AWS 실행 role과 Lambda/Function URL 생성 권한 확인
- 저장소 밖 경로로 실제 환경 변수 주입
- Function URL `/health` 200 확인
- Neon, TMAP 1회, OpenAI road/product 각 1회 smoke 확인
- 자격 증명, 권한 또는 Linux runtime이 없으면 `SMOKE_BLOCKED_BY_ENV: <비밀값 없는 근거>`로 분리 보고

롤백은 직전 검증 artifact를 `update-function-code`로 다시 올리는 범위로 제한한다.
