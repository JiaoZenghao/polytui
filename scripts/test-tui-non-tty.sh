#!/bin/sh
set -eu

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/tui-non-tty.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

version="$(cat VERSION)"
non_tty_diagnostic="polytui: interactive mode requires a TTY"

(cd implementations/go && go build -o "$tmp_dir/polytui-go" ./cmd/polytui)

fail() {
	printf '%s\n' "$1" >&2
	exit 1
}

assert_exact_file() {
	actual_file="$1"
	expected_file="$2"
	label="$3"

	if ! cmp -s "$actual_file" "$expected_file"; then
		printf '%s: output mismatch\nexpected:\n' "$label" >&2
		sed -n '1,120p' "$expected_file" >&2
		printf 'actual:\n' >&2
		sed -n '1,120p' "$actual_file" >&2
		exit 1
	fi
}

run_application_entry() {
	case "$1" in
	go) "$tmp_dir/polytui-go" ;;
	rust) cargo run --quiet --manifest-path implementations/rust/Cargo.toml -- ;;
	typescript) pnpm --dir implementations/typescript exec tsx src/index.ts ;;
	python) uv run --project implementations/python polytui ;;
	esac
}

check_application_entry() {
	language="$1"
	stdout_file="$tmp_dir/$language-application.stdout"
	stderr_file="$tmp_dir/$language-application.stderr"
	expected_file="$tmp_dir/$language-application.expected"

	set +e
	run_application_entry "$language" \
		</dev/null >"$stdout_file" 2>"$stderr_file"
	status=$?
	set -e

	[ "$status" -eq 2 ] ||
		fail "$language application entry: expected status 2, got $status"
	[ ! -s "$stdout_file" ] ||
		fail "$language application entry: expected empty stdout"

	printf '%s\n' "$non_tty_diagnostic" >"$expected_file"
	assert_exact_file "$stderr_file" "$expected_file" \
		"$language application entry stderr"
}

check_make_wrapper() {
	language="$1"
	stdout_file="$tmp_dir/$language-make.stdout"
	stderr_file="$tmp_dir/$language-make.stderr"

	set +e
	make --no-print-directory "run-$language" \
		</dev/null >"$stdout_file" 2>"$stderr_file"
	status=$?
	set -e

	[ "$status" -eq 2 ] ||
		fail "$language Make wrapper: expected status 2, got $status"
	[ ! -s "$stdout_file" ] ||
		fail "$language Make wrapper: expected empty stdout"

	set +e
	diagnostic_count="$(
		grep -Fxc "$non_tty_diagnostic" "$stderr_file"
	)"
	grep_status=$?
	set -e
	[ "$grep_status" -eq 0 ] ||
		fail "$language Make wrapper: missing complete diagnostic line"
	[ "$diagnostic_count" -eq 1 ] ||
		fail "$language Make wrapper: expected diagnostic exactly once"

	last_stderr_byte="$(
		od -An -t x1 "$stderr_file" |
			awk 'NF { last = $NF } END { print last }'
	)"
	[ "$last_stderr_byte" = 0a ] ||
		fail "$language Make wrapper: stderr is not newline terminated"
}

check_make_version() {
	language="$1"
	stdout_file="$tmp_dir/$language-version.stdout"
	stderr_file="$tmp_dir/$language-version.stderr"
	expected_file="$tmp_dir/$language-version.expected"

	set +e
	make --no-print-directory "run-$language" ARGS="--version" \
		</dev/null >"$stdout_file" 2>"$stderr_file"
	status=$?
	set -e

	[ "$status" -eq 0 ] ||
		fail "$language non-TTY version: expected status 0, got $status"
	[ ! -s "$stderr_file" ] ||
		fail "$language non-TTY version: expected empty stderr"

	printf 'polytui %s (%s)\n' "$version" "$language" >"$expected_file"
	assert_exact_file "$stdout_file" "$expected_file" \
		"$language non-TTY version stdout"
}

for language in go rust typescript python; do
	check_application_entry "$language"
done

for language in go rust typescript python; do
	check_make_wrapper "$language"
done

for language in go rust typescript python; do
	check_make_version "$language"
done

printf '%s\n' "all TUI non-TTY scenarios pass"
