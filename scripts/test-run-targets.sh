#!/bin/sh
set -eu

version="$(cat VERSION)"

check_target() {
	target="$1"
	language="$2"
	expected="polytui $version ($language)"
	output="$(make --no-print-directory "$target" ARGS="--version")"

	if [ "$output" != "$expected" ]; then
		printf '%s: expected "%s", got "%s"\n' "$target" "$expected" "$output" >&2
		exit 1
	fi
}

check_target run-go go
check_target run-rust rust
check_target run-typescript typescript
check_target run-python python

printf '%s\n' "all local run targets report language-specific versions based on $version"
