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

output_dir="${repo_root}/artifacts/${language}"
binary="${output_dir}/polytui"
archive="${output_dir}/polytui-${language}-macos-${architecture}.tar.gz"
mkdir -p "$output_dir"
rm -f "$binary" "$archive"

case "$language" in
	go)
		(
			cd "${repo_root}/implementations/go"
			go build -trimpath -o "$binary" ./cmd/polytui
		)
		;;
	rust)
		cargo build --release --locked \
			--manifest-path "${repo_root}/implementations/rust/Cargo.toml"
		cp "${repo_root}/implementations/rust/target/release/polytui" "$binary"
		;;
esac

chmod 755 "$binary"
tar -czf "$archive" -C "$output_dir" polytui
printf '%s\n' "$archive"
