#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

cd "${repo_root}"
uvx --from check-jsonschema==0.37.4 \
  check-jsonschema \
  --schemafile contracts/schema/scenario.schema.json \
  contracts/scenarios/*.json
uvx --from check-jsonschema==0.37.4 \
  check-jsonschema \
  --schemafile contracts/schema/lifecycle.schema.json \
  contracts/lifecycle/*.json
