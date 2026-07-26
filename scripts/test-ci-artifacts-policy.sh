#!/bin/sh
set -eu

validator="./scripts/validate-ci-artifacts.sh"
base_workflow=".github/workflows/ci.yml"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/ci-artifacts-policy.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

expect_accepted() {
	label="$1"
	workflow="$2"
	output="$tmp_dir/$label.out"

	if ! CI_WORKFLOW_PATH="$workflow" "$validator" >"$output" 2>&1; then
		printf 'not ok - %s should be accepted\n' "$label" >&2
		sed -n '1,120p' "$output" >&2
		exit 1
	fi

	printf 'ok - %s\n' "$label"
}

expect_rejected() {
	label="$1"
	workflow="$2"
	diagnostic="$3"
	output="$tmp_dir/$label.out"

	if CI_WORKFLOW_PATH="$workflow" "$validator" >"$output" 2>&1; then
		printf 'not ok - %s should be rejected\n' "$label" >&2
		sed -n '1,120p' "$output" >&2
		exit 1
	fi

	if ! grep -Fq -- "$diagnostic" "$output"; then
		printf 'not ok - %s missing diagnostic: %s\n' \
			"$label" "$diagnostic" >&2
		sed -n '1,120p' "$output" >&2
		exit 1
	fi

	printf 'ok - %s\n' "$label"
}

make_named_upload() {
	output="$1"
	job="$2"
	step="$3"
	action="$4"

	awk -v job="$job" -v step="$step" -v action="$action" '
		{ print }
		END {
			print ""
			print "  " job ":"
			print "    runs-on: macos-latest"
			print "    steps:"
			print "      - name: " step
			print "        uses: " action
		}
	' "$base_workflow" >"$output"
}

make_unnamed_upload() {
	output="$1"

	awk '
		{ print }
		END {
			print ""
			print "  policy-extra-unnamed:"
			print "    runs-on: macos-latest"
			print "    steps:"
			print "      - uses: actions/upload-artifact@v7"
		}
	' "$base_workflow" >"$output"
}

make_duplicate_upload() {
	output="$1"

	awk '
		$0 == "  test-rust-macos:" {
			print "      - name: Upload Go artifact"
			print "        uses: actions/upload-artifact@v7"
			print ""
		}
		{ print }
	' "$base_workflow" >"$output"
}

make_step_continue_on_error() {
	output="$1"

	awk '
		{ print }
		$0 == "      - name: Upload Go artifact" {
			print "        continue-on-error: true"
		}
	' "$base_workflow" >"$output"
}

make_job_continue_on_error() {
	output="$1"
	job="$2"

	awk -v job="$job" '
		{ print }
		$0 == "  " job ":" {
			print "    continue-on-error: true"
		}
	' "$base_workflow" >"$output"
}

make_wrong_path() {
	output="$1"

	awk '
		$0 == "          path: artifacts/go/polytui-go-macos-${{ runner.arch }}.tar.gz" {
			print "          path: artifacts/go/wrong.tar.gz"
			next
		}
		{ print }
	' "$base_workflow" >"$output"
}

expect_accepted baseline "$base_workflow"

make_named_upload "$tmp_dir/extra-v7.yml" \
	policy-extra-v7 "Upload extra v7" "actions/upload-artifact@v7"
expect_rejected extra-v7 "$tmp_dir/extra-v7.yml" \
	"artifact upload steps: expected exactly 4 uploads, found 5"

make_named_upload "$tmp_dir/extra-v6.yml" \
	policy-extra-v6 "Upload extra v6" "actions/upload-artifact@v6"
expect_rejected extra-v6 "$tmp_dir/extra-v6.yml" \
	"artifact upload steps: expected exactly 4 uploads, found 5"

make_named_upload "$tmp_dir/extra-sha.yml" \
	policy-extra-sha "Upload extra SHA" \
	"actions/upload-artifact@0123456789abcdef0123456789abcdef01234567"
expect_rejected extra-sha "$tmp_dir/extra-sha.yml" \
	"artifact upload steps: expected exactly 4 uploads, found 5"

make_named_upload "$tmp_dir/extra-double-quoted.yml" \
	policy-extra-double-quoted "Upload extra double quoted" \
	'"actions/upload-artifact@v7" # pinned major'
expect_rejected extra-double-quoted "$tmp_dir/extra-double-quoted.yml" \
	"artifact upload steps: expected exactly 4 uploads, found 5"

make_named_upload "$tmp_dir/extra-single-quoted.yml" \
	policy-extra-single-quoted "Upload extra single quoted" \
	"'actions/upload-artifact@v7' # pinned major"
expect_rejected extra-single-quoted "$tmp_dir/extra-single-quoted.yml" \
	"artifact upload steps: expected exactly 4 uploads, found 5"

make_duplicate_upload "$tmp_dir/duplicate.yml"
expect_rejected duplicate "$tmp_dir/duplicate.yml" \
	'artifact upload steps: expected 1 exact line(s) "test-go-macos / Upload Go artifact", found 2'

make_unnamed_upload "$tmp_dir/unnamed.yml"
expect_rejected unnamed "$tmp_dir/unnamed.yml" \
	"artifact upload steps: expected exactly 4 uploads, found 5"

make_step_continue_on_error "$tmp_dir/step-continue-on-error.yml"
expect_rejected step-continue-on-error "$tmp_dir/step-continue-on-error.yml" \
	"test-go-macos / Upload Go artifact: continue-on-error is not allowed"

make_job_continue_on_error "$tmp_dir/go-job-continue-on-error.yml" \
	test-go-macos
expect_rejected go-job-continue-on-error \
	"$tmp_dir/go-job-continue-on-error.yml" \
	"test-go-macos: job-level continue-on-error is not allowed"

make_job_continue_on_error "$tmp_dir/rust-job-continue-on-error.yml" \
	test-rust-macos
expect_rejected rust-job-continue-on-error \
	"$tmp_dir/rust-job-continue-on-error.yml" \
	"test-rust-macos: job-level continue-on-error is not allowed"

make_job_continue_on_error "$tmp_dir/typescript-job-continue-on-error.yml" \
	test-typescript-macos
expect_rejected typescript-job-continue-on-error \
	"$tmp_dir/typescript-job-continue-on-error.yml" \
	"test-typescript-macos: job-level continue-on-error is not allowed"

make_job_continue_on_error "$tmp_dir/python-job-continue-on-error.yml" \
	test-python-macos-uv
expect_rejected python-job-continue-on-error \
	"$tmp_dir/python-job-continue-on-error.yml" \
	"test-python-macos-uv: job-level continue-on-error is not allowed"

make_wrong_path "$tmp_dir/wrong-path.yml"
expect_rejected wrong-path "$tmp_dir/wrong-path.yml" \
	'path: artifacts/go/polytui-go-macos-${{ runner.arch }}.tar.gz'

printf '%s\n' "CI artifact policy regressions pass"
