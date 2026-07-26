#!/bin/sh
set -eu

workflow=".github/workflows/ci.yml"

assert_count() {
	needle="$1"
	expected="$2"
	actual="$(grep -F -c -- "$needle" "$workflow" || true)"

	if [ "$actual" -ne "$expected" ]; then
		printf 'expected %s occurrences of "%s", found %s\n' \
			"$expected" "$needle" "$actual" >&2
		exit 1
	fi
}

assert_present() {
	needle="$1"
	if ! grep -F -q -- "$needle" "$workflow"; then
		printf 'missing workflow policy: %s\n' "$needle" >&2
		exit 1
	fi
}

assert_count "uses: actions/upload-artifact@v7" 4
assert_count "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" 4
assert_count "retention-days: 30" 4
assert_count "if-no-files-found: error" 4

assert_present "name: Build Go artifact"
assert_present "name: Build Rust artifact"
assert_present "name: Build TypeScript artifact"
assert_present "name: Build Python artifact"
assert_present "name: polytui-go-macos-\${{ runner.arch }}"
assert_present "name: polytui-rust-macos-\${{ runner.arch }}"
assert_present "name: polytui-typescript"
assert_present "name: polytui-python"

printf '%s\n' "GitHub Actions artifact policy is valid"
