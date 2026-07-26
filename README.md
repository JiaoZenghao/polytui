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
cd implementations/go && go run ./cmd/polytui --version
cargo run --quiet --manifest-path implementations/rust/Cargo.toml -- --version
pnpm --dir implementations/typescript exec tsx src/index.ts --version
uv run --project implementations/python polytui --version
```

The architecture and approved scope are documented under
`docs/superpowers/specs/`.
