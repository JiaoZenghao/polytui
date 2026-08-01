# PolyTUI

PolyTUI implements the same CLI/TUI application independently in Go, Rust,
TypeScript, and Python. The repository compares each language's idiomatic
approach while enforcing one shared behavior contract.

## Current scope

M1 is macOS-only. The implemented vertical slices provide shared contract
validation, four synchronized `polytui --version` entry points, and a minimal
language-specific inline startup TUI. The TUI exits cleanly with `Ctrl+C` or
`Ctrl+D`; it does not yet provide editing, streaming, or model access.

## Prerequisites

- Go 1.26.5
- Rust 1.97.1
- Node.js 24.15.0
- pnpm 10.33.2
- Python 3.13.14
- uv 0.8.9

## Verify everything

```sh
make test
```

## Run each implementation

To start each implementation's interactive startup view, use a real terminal:

```sh
make run-go
make run-rust
make run-typescript
make run-python
```

The inline TUI requires a real TTY. Press `Ctrl+C` or `Ctrl+D` to exit cleanly.

For scripts and CI, `--version` and `--help` remain usable without an
interactive terminal:

```sh
make run-go ARGS="--version"
make run-rust ARGS="--version"
make run-typescript ARGS="--version"
make run-python ARGS="--version"
```

Before the first TypeScript run, install its locked dependencies with:

```sh
pnpm --dir implementations/typescript install --frozen-lockfile
```

## Download CI artifacts

Successful pushes to `main` publish four artifacts from the macOS CI workflow:

- `polytui-go-macos-<architecture>`
- `polytui-rust-macos-<architecture>`
- `polytui-typescript`
- `polytui-python`

Open the successful workflow run on the repository's **Actions** tab and
download the artifact from its **Artifacts** section. Artifacts are retained
for 30 days. Pull request runs build and test the projects but do not upload
artifacts.

For Go or Rust, unzip the GitHub artifact and then extract its native archive:

```sh
tar -xzf polytui-go-macos-ARM64.tar.gz
./polytui --version
```

The inner `tar.gz` preserves the executable permission of `polytui`.

M1 artifacts are not signed with an Apple Developer ID and are not notarized.
If macOS blocks a build that you produced or downloaded from this trusted
repository, open **System Settings > Privacy & Security** and choose
**Open Anyway** for `polytui`. Executable permission and Apple notarization are
separate concerns.

The architecture and approved scope are documented under
`docs/superpowers/specs/`.
