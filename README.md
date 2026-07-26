# PolyTUI

PolyTUI implements the same CLI/TUI application independently in Go, Rust,
TypeScript, and Python. The repository compares each language's idiomatic
approach while enforcing one shared behavior contract.

## Current scope

M1 is macOS-only. The first vertical slice provides shared contract validation
and four synchronized `polytui --version` entry points. It does not start a TUI
or call a model.

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

```sh
make run-go ARGS="--version"
make run-rust ARGS="--version"
make run-typescript ARGS="--version"
make run-python ARGS="--version"
```

Omit `ARGS` to run the CLI without arguments. Before the first TypeScript run,
install its locked dependencies with:

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

The architecture and approved scope are documented under
`docs/superpowers/specs/`.
