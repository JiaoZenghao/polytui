#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
version="$(tr -d '\n' < "${repo_root}/VERSION")"

check_version() {
  local language="$1"
  local expected="polytui ${version} (${language})"
  shift

  local actual
  actual="$("$@")"
  if [[ "${actual}" != "${expected}" ]]; then
    printf 'version mismatch for %s\nexpected: %s\nactual:   %s\n' \
      "${language}" "${expected}" "${actual}" >&2
    return 1
  fi
}

check_version go \
  bash -c "cd '${repo_root}/implementations/go' && go run ./cmd/polytui --version"
check_version rust \
  cargo run --quiet --locked \
    --manifest-path "${repo_root}/implementations/rust/Cargo.toml" \
    -- --version
check_version typescript \
  pnpm --dir "${repo_root}/implementations/typescript" \
    exec tsx src/index.ts --version
check_version python \
  uv run --project "${repo_root}/implementations/python" \
    polytui --version

printf 'all implementations report %s\n' "${version}"
