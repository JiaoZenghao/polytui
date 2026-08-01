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

check_typescript_startup_structure() {
	expected='node implementations/typescript/dist/index.js --version'
	actual="$(make --no-print-directory -n run-typescript ARGS="--version")"

	if [ "$actual" != "$expected" ]; then
		printf '%s\nexpected:' "run-typescript cached startup structure mismatch" >&2
		printf '%s\n' "$expected" >&2
		printf '%s\nactual:' >&2
		printf '%s\n' "$actual" >&2
		exit 1
	fi

	expected='pnpm --dir implementations/typescript exec tsc -p tsconfig.json
node implementations/typescript/dist/index.js --version'
	actual="$(make --no-print-directory -B -n run-typescript ARGS="--version")"

	if [ "$actual" != "$expected" ]; then
		printf '%s\nexpected:' "run-typescript forced startup structure mismatch" >&2
		printf '%s\n' "$expected" >&2
		printf '%s\nactual:' >&2
		printf '%s\n' "$actual" >&2
		exit 1
	fi
}

check_target run-go go
check_target run-rust rust
check_target run-typescript typescript
check_typescript_startup_structure
check_target run-python python

printf '%s\n' "all local run targets report language-specific versions based on $version"
