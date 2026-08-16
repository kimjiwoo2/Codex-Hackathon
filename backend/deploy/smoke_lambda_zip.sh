#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "${script_dir}/.." && pwd)"
archive_path="${1:-${backend_dir}/dist/backend-lambda.zip}"
smoke_root="$(mktemp -d)"

cleanup() {
  rm -rf "${smoke_root}"
}
trap cleanup EXIT

uv run --frozen --project "${backend_dir}" python \
  "${script_dir}/validate_lambda_zip.py" "${archive_path}"
uv run --frozen --project "${backend_dir}" python -m zipfile -e "${archive_path}" "${smoke_root}"

smoke_code='import app, httpx, mangum, openai, psycopg; from app.lambda_handler import handler; print("LAMBDA_IMPORT_SMOKE=ok"); print(f"HANDLER_TYPE={type(handler).__name__}")'

if [[ "$(uname -s)" == "Linux" && "$(uname -m)" == "x86_64" ]] && command -v python3.12 >/dev/null 2>&1; then
  PYTHONPATH="${smoke_root}" python3.12 -c "${smoke_code}"
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  docker run --rm --platform linux/amd64 \
    --volume "${smoke_root}:/var/task:ro" \
    --entrypoint python \
    public.ecr.aws/lambda/python:3.12 \
    -c "import sys; sys.path.insert(0, '/var/task'); ${smoke_code}"
  exit 0
fi

echo "SMOKE_BLOCKED_BY_ENV: Linux x86_64 Python 3.12 or Docker is required" >&2
exit 2
