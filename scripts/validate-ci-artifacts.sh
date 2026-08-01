#!/bin/sh
set -eu

workflow="${CI_WORKFLOW_PATH:-.github/workflows/ci.yml}"

job_block() {
	job="$1"
	awk -v target="$job" '
		$0 == "  " target ":" { inside = 1 }
		inside && $0 ~ /^  [[:alnum:]_-]+:$/ && $0 != "  " target ":" { exit }
		inside { print }
	' "$workflow"
}

step_block() {
	job="$1"
	step="$2"
	job_block "$job" | awk -v target="$step" '
		$0 == "      - name: " target { inside = 1 }
		inside && $0 ~ /^      - / && $0 != "      - name: " target { exit }
		inside { print }
	'
}

upload_pairs() {
	awk '
		/^  [[:alnum:]_-]+:$/ {
			job = $0
			sub(/^  /, "", job)
			sub(/:$/, "", job)
		}
		/^      - / {
			step = "<unnamed>"
			if ($0 ~ /^      - name: /) {
				step = $0
				sub(/^      - name: /, "", step)
			}
		}
		/^[[:space:]]*(- )?uses:[[:space:]]+/ {
			value = $0
			sub(/^[[:space:]]*(- )?uses:[[:space:]]+/, "", value)
			quote = substr(value, 1, 1)
			if (quote == "\"" || quote == sprintf("%c", 39)) {
				value = substr(value, 2)
				closing_quote = index(value, quote)
				if (closing_quote > 0) {
					value = substr(value, 1, closing_quote - 1)
				}
			} else {
				sub(/[[:space:]]+#.*$/, "", value)
				sub(/[[:space:]]+$/, "", value)
			}
			if (value ~ /^actions\/upload-artifact@/) {
				print job " / " step
			}
		}
	' "$workflow"
}

assert_exact_line() {
	scope="$1"
	content="$2"
	line="$3"
	expected="${4:-1}"
	actual="$(printf '%s\n' "$content" | grep -Fxc -- "$line" || true)"

	if [ "$actual" -ne "$expected" ]; then
		printf '%s: expected %s exact line(s) "%s", found %s\n' \
			"$scope" "$expected" "$line" "$actual" >&2
		exit 1
	fi
}

assert_job_line() {
	job="$1"
	line="$2"
	assert_exact_line "$job" "$(job_block "$job")" "$line"
}

assert_step_line() {
	job="$1"
	step="$2"
	line="$3"
	block="$(step_block "$job" "$step")"

	if [ -z "$block" ]; then
		printf '%s / %s: missing step\n' "$job" "$step" >&2
		exit 1
	fi

	assert_exact_line "$job / $step" "$block" "$line"
}

assert_upload_pairs() {
	pairs="$(upload_pairs)"

	assert_exact_line "artifact upload steps" "$pairs" \
		"test-go-macos / Upload Go artifact"
	assert_exact_line "artifact upload steps" "$pairs" \
		"test-rust-macos / Upload Rust artifact"
	assert_exact_line "artifact upload steps" "$pairs" \
		"test-typescript-macos / Upload TypeScript artifact"
	assert_exact_line "artifact upload steps" "$pairs" \
		"test-python-macos-uv / Upload Python artifact"

	actual="$(printf '%s\n' "$pairs" | grep -c . || true)"
	if [ "$actual" -ne 4 ]; then
		printf 'artifact upload steps: expected exactly 4 uploads, found %s\n' \
			"$actual" >&2
		exit 1
	fi
}

assert_no_job_continue_on_error() {
	job="$1"
	block="$(job_block "$job")"
	actual="$(printf '%s\n' "$block" |
		grep -Ec '^    continue-on-error[[:space:]]*:' || true)"

	if [ "$actual" -ne 0 ]; then
		printf '%s: job-level continue-on-error is not allowed\n' \
			"$job" >&2
		exit 1
	fi
}

assert_no_step_continue_on_error() {
	job="$1"
	step="$2"
	block="$(step_block "$job" "$step")"
	actual="$(printf '%s\n' "$block" |
		grep -Ec '^[[:space:]]*continue-on-error[[:space:]]*:' || true)"

	if [ "$actual" -ne 0 ]; then
		printf '%s / %s: continue-on-error is not allowed\n' \
			"$job" "$step" >&2
		exit 1
	fi
}

assert_upload() {
	job="$1"
	step="$2"
	name="$3"
	path="$4"
	assert_no_job_continue_on_error "$job"
	assert_no_step_continue_on_error "$job" "$step"
	assert_step_line "$job" "$step" "        if: github.event_name == 'push' && github.ref == 'refs/heads/main'"
	assert_step_line "$job" "$step" "        uses: actions/upload-artifact@v7"
	assert_step_line "$job" "$step" "          name: $name"
	assert_step_line "$job" "$step" "          path: $path"
	assert_step_line "$job" "$step" "          retention-days: 30"
	assert_step_line "$job" "$step" "          if-no-files-found: error"
}

assert_upload_pairs

assert_job_line validate-contracts "      - run: ./scripts/validate-contracts.sh"
assert_job_line validate-contracts "      - run: ./scripts/validate-ci-artifacts.sh"
assert_job_line validate-contracts "      - run: ./scripts/test-ci-artifacts-policy.sh"
assert_job_line blackbox-parity-macos "      - run: ./scripts/check-versions.sh"
assert_job_line blackbox-parity-macos "      - run: ./scripts/test-run-targets.sh"
assert_job_line blackbox-parity-macos "      - run: make test-tui-non-tty"
assert_job_line blackbox-parity-macos "      - run: make test-tui-lifecycle"

assert_step_line test-go-macos "Build and verify Go artifact" \
	'        run: ./scripts/test-native-artifact-archive.sh go "${{ runner.arch }}"'
assert_upload test-go-macos "Upload Go artifact" \
	'polytui-go-macos-${{ runner.arch }}' \
	'artifacts/go/polytui-go-macos-${{ runner.arch }}.tar.gz'

assert_step_line test-rust-macos "Build and verify Rust artifact" \
	'        run: ./scripts/test-native-artifact-archive.sh rust "${{ runner.arch }}"'
assert_upload test-rust-macos "Upload Rust artifact" \
	'polytui-rust-macos-${{ runner.arch }}' \
	'artifacts/rust/polytui-rust-macos-${{ runner.arch }}.tar.gz'

assert_step_line test-typescript-macos "Build TypeScript artifact" \
	"        run: pnpm run build"
assert_step_line test-typescript-macos "Stage TypeScript artifact" \
	"          cp -R dist ../../artifacts/typescript/dist"
assert_step_line test-typescript-macos "Stage TypeScript artifact" \
	"          cp package.json ../../artifacts/typescript/package.json"
assert_upload test-typescript-macos "Upload TypeScript artifact" \
	"polytui-typescript" "artifacts/typescript"

assert_step_line test-python-macos-uv "Build Python artifact" \
	"        run: uv build --out-dir ../../artifacts/python"
assert_upload test-python-macos-uv "Upload Python artifact" \
	"polytui-python" "artifacts/python"

printf '%s\n' "GitHub Actions artifact policy is valid"
