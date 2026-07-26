#!/bin/sh
set -eu

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "${script_dir}/.." && pwd)"
language="${1:-}"
architecture="${2:-}"

case "$language" in
	go|rust) ;;
	*)
		printf 'usage: %s <go|rust> <architecture>\n' "$0" >&2
		exit 2
		;;
esac

if [ -z "$architecture" ]; then
	printf 'architecture is required\n' >&2
	exit 2
fi

archive="$("${script_dir}/build-native-artifact.sh" "$language" "$architecture")"
expected="${repo_root}/artifacts/${language}/polytui-${language}-macos-${architecture}.tar.gz"

if [ "$archive" != "$expected" ] || [ ! -f "$archive" ]; then
	printf 'expected archive %s, got %s\n' "$expected" "$archive" >&2
	exit 1
fi

extract_dir="$(mktemp -d)"
trap 'rm -rf "$extract_dir"' EXIT HUP INT TERM
tar -xzf "$archive" -C "$extract_dir"

binary="${extract_dir}/polytui"
if [ ! -x "$binary" ]; then
	printf 'archive member is not executable: %s\n' "$binary" >&2
	exit 1
fi

version="$(tr -d '\n' < "${repo_root}/VERSION")"
expected_version="polytui ${version} (${language})"
actual_version="$("$binary" --version)"

if [ "$actual_version" != "$expected_version" ]; then
	printf 'expected "%s", got "%s"\n' "$expected_version" "$actual_version" >&2
	exit 1
fi

printf 'verified %s\n' "$archive"
