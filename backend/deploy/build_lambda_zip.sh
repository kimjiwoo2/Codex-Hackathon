#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend_dir="$(cd "${script_dir}/.." && pwd)"
output_path="${1:-${backend_dir}/dist/backend-lambda.zip}"
build_root="$(mktemp -d)"
package_dir="${build_root}/package"
requirements_file="${build_root}/requirements-lambda.txt"

cleanup() {
  rm -rf "${build_root}"
}
trap cleanup EXIT

command -v uv >/dev/null 2>&1 || {
  echo "uv is required to build the Lambda archive" >&2
  exit 1
}

mkdir -p "${package_dir}" "$(dirname "${output_path}")"

uv export --quiet \
  --project "${backend_dir}" \
  --frozen \
  --no-dev \
  --no-emit-project \
  --format requirements.txt \
  --output-file "${requirements_file}"

uv pip install \
  --requirements "${requirements_file}" \
  --target "${package_dir}" \
  --python-platform x86_64-manylinux_2_28 \
  --python-version 3.12 \
  --require-hashes \
  --only-binary :all:

cp -R "${backend_dir}/src/app" "${package_dir}/app"
find "${package_dir}" -type d -name __pycache__ -prune -exec rm -rf {} +
rm -rf "${package_dir}/bin"

uv run --frozen --project "${backend_dir}" python \
  "${script_dir}/create_lambda_zip.py" "${package_dir}" "${output_path}"
uv run --frozen --project "${backend_dir}" python \
  "${script_dir}/validate_lambda_zip.py" "${output_path}"

echo "ARTIFACT=$(cd "$(dirname "${output_path}")" && pwd)/$(basename "${output_path}")"
