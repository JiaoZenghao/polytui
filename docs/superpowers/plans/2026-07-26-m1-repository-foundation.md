# M1 Repository Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the `polytui` monorepo foundation with a validated shared scenario, four buildable CLI entry points, synchronized version reporting, root developer commands, and six macOS GitHub Actions checks.

**Architecture:** The root owns portable contracts, version identity, orchestration scripts, documentation, and CI. Go, Rust, TypeScript, and Python remain independent projects and expose the same `polytui --version` behavior without importing source from one another. This slice does not start an interactive terminal or add TUI framework dependencies; those belong to the next vertical slice.

**Tech Stack:** Bash, GNU Make as shipped with macOS, JSON Schema Draft 2020-12, `check-jsonschema` 0.37.4 through `uvx`, Go 1.26.5 with Cobra 1.10.2, Rust 1.97.1 with Clap 4.6.4, Node.js 24.15.0 with pnpm 10.33.2 and Commander 15.0.0, Python 3.13.14 with uv 0.8.9 and Typer 0.27.0, GitHub Actions macOS runners.

## Global Constraints

- The project name, GitHub repository name, release name, package identity, and all four user-facing commands are `polytui`.
- Support macOS only in M1.
- Keep implementations under `implementations/go`, `implementations/rust`, `implementations/typescript`, and `implementations/python`.
- Implementations must not import source code from one another.
- Treat `contracts/` as the behavior source of truth.
- Use synchronized vertical slices: a slice is complete only when all four language checks pass.
- Use `VERSION` as the SemVer source of truth.
- Use `0.1.0-dev.0` while developing M1; reserve `0.1.0` for the completed M1 release.
- Every `polytui --version` command must print `polytui 0.1.0-dev.0 (<language>)` followed by one newline.
- Python package metadata uses the PEP 440 equivalent `0.1.0.dev0`, while its CLI reports the root SemVer `0.1.0-dev.0`.
- Manage Python exclusively with uv; commit `uv.lock`; do not create `requirements.txt`, Pipenv, or Poetry files.
- Manage TypeScript with pnpm and commit `pnpm-lock.yaml`.
- Commit `go.sum` and `Cargo.lock`.
- Keep `AGENTS.md` unchanged unless the user explicitly asks to version it.
- Do not add TUI frameworks in this slice.

## External GitHub Prerequisite

Local `gh auth status` identifies the intended account as `JiaoZenghao`, but its
stored token is currently invalid. This plan creates and verifies the workflow
file locally. Before the first push, reconnect that account or use the connected
GitHub app, then explicitly choose whether `JiaoZenghao/polytui` is public or
private. Do not create the remote repository or push without that choice.

---

## Planned File Map

### Root and shared contracts

- `VERSION` — root SemVer source of truth.
- `README.md` — contributor entry point and root commands.
- `CHANGELOG.md` — synchronized monorepo change history.
- `Makefile` — root orchestration without embedding language business logic.
- `contracts/schema/scenario.schema.json` — shared simulated-stream scenario schema.
- `contracts/scenarios/hello.json` — first valid deterministic scenario.
- `scripts/validate-contracts.sh` — pinned JSON Schema validation entry point.
- `scripts/check-versions.sh` — cross-language version parity check.

### Go

- `implementations/go/go.mod` and `go.sum` — independent Go module.
- `implementations/go/internal/buildinfo/buildinfo.go` — Go version identity.
- `implementations/go/internal/cli/root.go` — Cobra root command.
- `implementations/go/internal/cli/root_test.go` — CLI version behavior test.
- `implementations/go/cmd/polytui/main.go` — executable entry point.

### Rust

- `implementations/rust/Cargo.toml` and `Cargo.lock` — independent Cargo package.
- `implementations/rust/src/build_info.rs` — Rust version identity.
- `implementations/rust/src/cli.rs` — Clap parser.
- `implementations/rust/src/lib.rs` — testable library exports.
- `implementations/rust/src/main.rs` — executable entry point.

### TypeScript

- `implementations/typescript/package.json` and `pnpm-lock.yaml` — independent pnpm project.
- `implementations/typescript/tsconfig.json` — Node ESM TypeScript build.
- `implementations/typescript/src/build-info.ts` — TypeScript version identity.
- `implementations/typescript/src/cli.ts` — Commander program factory.
- `implementations/typescript/src/index.ts` — executable entry point.
- `implementations/typescript/test/cli.test.ts` — CLI version behavior test.

### Python

- `implementations/python/pyproject.toml` and `uv.lock` — independent uv package.
- `implementations/python/src/polytui/build_info.py` — Python version identity.
- `implementations/python/src/polytui/cli.py` — Typer application.
- `implementations/python/src/polytui/__init__.py` and `__main__.py` — package and module entry points.
- `implementations/python/tests/test_cli.py` — CLI version behavior test.

### CI

- `.github/workflows/ci.yml` — six required macOS checks.

---

### Task 1: Root Version and Shared Contract Validation

**Files:**
- Create: `VERSION`
- Create: `contracts/schema/scenario.schema.json`
- Create: `contracts/scenarios/hello.json`
- Create: `scripts/validate-contracts.sh`

**Interfaces:**
- Consumes: uv 0.8.9 or newer and `check-jsonschema==0.37.4`.
- Produces: `VERSION` containing exactly `0.1.0-dev.0`; scenario format version `1`; executable command `scripts/validate-contracts.sh`.

- [ ] **Step 1: Create the root version source**

Create `VERSION` with exactly:

```text
0.1.0-dev.0
```

- [ ] **Step 2: Write the schema and intentionally incomplete scenario**

Create `contracts/schema/scenario.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/JiaoZenghao/polytui/contracts/schema/scenario.schema.json",
  "title": "PolyTUI deterministic stream scenario",
  "type": "object",
  "required": ["format_version", "id", "prompt", "chunks"],
  "properties": {
    "format_version": {
      "const": 1
    },
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$"
    },
    "prompt": {
      "type": "string",
      "minLength": 1
    },
    "chunks": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "failure": {
      "type": "object",
      "required": ["after_chunk", "message"],
      "properties": {
        "after_chunk": {
          "type": "integer",
          "minimum": 0
        },
        "message": {
          "type": "string",
          "minLength": 1
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

Create the intentionally invalid `contracts/scenarios/hello.json`:

```json
{
  "format_version": 1,
  "id": "hello",
  "prompt": "hello"
}
```

- [ ] **Step 3: Add the pinned validator command**

Create `scripts/validate-contracts.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"

cd "${repo_root}"
uvx --from check-jsonschema==0.37.4 \
  check-jsonschema \
  --schemafile contracts/schema/scenario.schema.json \
  contracts/scenarios/*.json
```

Mark it executable:

```bash
chmod +x scripts/validate-contracts.sh
```

- [ ] **Step 4: Run validation to verify it fails**

Run:

```bash
./scripts/validate-contracts.sh
```

Expected: exit code `1` and an error stating that `chunks` is a required property in `contracts/scenarios/hello.json`.

- [ ] **Step 5: Complete the deterministic scenario**

Replace `contracts/scenarios/hello.json` with:

```json
{
  "format_version": 1,
  "id": "hello",
  "prompt": "hello",
  "chunks": [
    "Hello",
    " from",
    " polytui."
  ]
}
```

- [ ] **Step 6: Run validation to verify it passes**

Run:

```bash
./scripts/validate-contracts.sh
```

Expected: exit code `0` and output ending with `ok -- validation done`.

- [ ] **Step 7: Commit the shared foundation**

```bash
git add VERSION contracts scripts/validate-contracts.sh
git commit -m "feat(contracts): add versioned stream scenario"
```

---

### Task 2: Go CLI Entry Point

**Files:**
- Create: `implementations/go/go.mod`
- Create: `implementations/go/go.sum`
- Create: `implementations/go/internal/buildinfo/buildinfo.go`
- Create: `implementations/go/internal/cli/root_test.go`
- Create: `implementations/go/internal/cli/root.go`
- Create: `implementations/go/cmd/polytui/main.go`

**Interfaces:**
- Consumes: root version value `0.1.0-dev.0`.
- Produces: `buildinfo.String() string`; `cli.NewRootCommand() *cobra.Command`; `go run ./cmd/polytui --version` prints `polytui 0.1.0-dev.0 (go)`.

- [ ] **Step 1: Initialize the Go module and add Cobra**

Run:

```bash
cd implementations/go
go mod init github.com/JiaoZenghao/polytui/implementations/go
go get github.com/spf13/cobra@v1.10.2
```

Expected: `go.mod` and `go.sum` exist and `go.mod` declares Go `1.26.5` or the compatible `1.26` language version selected by the toolchain.

- [ ] **Step 2: Write the failing CLI test**

Create `implementations/go/internal/cli/root_test.go`:

```go
package cli

import (
	"bytes"
	"testing"
)

func TestVersionFlag(t *testing.T) {
	t.Parallel()

	var output bytes.Buffer
	command := NewRootCommand()
	command.SetOut(&output)
	command.SetErr(&output)
	command.SetArgs([]string{"--version"})

	if err := command.Execute(); err != nil {
		t.Fatalf("Execute() error = %v", err)
	}

	const want = "polytui 0.1.0-dev.0 (go)\n"
	if got := output.String(); got != want {
		t.Fatalf("version output = %q, want %q", got, want)
	}
}
```

- [ ] **Step 3: Run the Go test to verify it fails**

Run:

```bash
cd implementations/go
go test ./internal/cli
```

Expected: FAIL because `NewRootCommand` is undefined.

- [ ] **Step 4: Add Go build identity**

Create `implementations/go/internal/buildinfo/buildinfo.go`:

```go
package buildinfo

import "fmt"

const (
	Version  = "0.1.0-dev.0"
	Language = "go"
)

func String() string {
	return fmt.Sprintf("polytui %s (%s)", Version, Language)
}
```

- [ ] **Step 5: Implement the Cobra root command**

Create `implementations/go/internal/cli/root.go`:

```go
package cli

import (
	"github.com/JiaoZenghao/polytui/implementations/go/internal/buildinfo"
	"github.com/spf13/cobra"
)

func NewRootCommand() *cobra.Command {
	command := &cobra.Command{
		Use:           "polytui",
		Short:         "Learn CLI/TUI development across four languages",
		SilenceErrors: true,
		SilenceUsage:  true,
		Version:       buildinfo.String(),
	}
	command.SetVersionTemplate("{{.Version}}\n")
	return command
}
```

- [ ] **Step 6: Add the Go executable**

Create `implementations/go/cmd/polytui/main.go`:

```go
package main

import (
	"fmt"
	"os"

	"github.com/JiaoZenghao/polytui/implementations/go/internal/cli"
)

func main() {
	if err := cli.NewRootCommand().Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
```

- [ ] **Step 7: Format and run the Go tests**

Run:

```bash
cd implementations/go
gofmt -w cmd internal
go test ./...
```

Expected: PASS.

- [ ] **Step 8: Verify the Go CLI**

Run:

```bash
cd implementations/go
go run ./cmd/polytui --version
```

Expected:

```text
polytui 0.1.0-dev.0 (go)
```

- [ ] **Step 9: Commit the Go entry point**

```bash
git add implementations/go
git commit -m "feat(go): add polytui CLI entry point"
```

---

### Task 3: Rust CLI Entry Point

**Files:**
- Create: `implementations/rust/Cargo.toml`
- Create: `implementations/rust/Cargo.lock`
- Create: `implementations/rust/src/build_info.rs`
- Create: `implementations/rust/src/cli.rs`
- Create: `implementations/rust/src/lib.rs`
- Create: `implementations/rust/src/main.rs`

**Interfaces:**
- Consumes: root version value `0.1.0-dev.0`.
- Produces: `build_info::VERSION_TEXT`; `cli::Cli`; `cargo run -- --version` prints `polytui 0.1.0-dev.0 (rust)`.

- [ ] **Step 1: Initialize the Rust package and add Clap**

Run:

```bash
cargo init --bin --name polytui implementations/rust
cd implementations/rust
cargo add clap@4.6.4 --features derive
```

Expected: `Cargo.toml`, `Cargo.lock`, and `src/main.rs` exist.

- [ ] **Step 2: Write the failing Rust version test**

Create `implementations/rust/src/lib.rs`:

```rust
pub mod build_info;
pub mod cli;

#[cfg(test)]
mod tests {
    use clap::CommandFactory;

    use crate::cli::Cli;

    #[test]
    fn version_flag_uses_shared_version() {
        let mut command = Cli::command();
        assert_eq!(
            command.render_version().to_string(),
            "polytui 0.1.0-dev.0 (rust)\n"
        );
    }
}
```

- [ ] **Step 3: Run the Rust test to verify it fails**

Run:

```bash
cd implementations/rust
cargo test
```

Expected: FAIL because modules `build_info` and `cli` do not exist.

- [ ] **Step 4: Add Rust build identity**

Create `implementations/rust/src/build_info.rs`:

```rust
pub const VERSION: &str = "0.1.0-dev.0";
pub const VERSION_TEXT: &str = "0.1.0-dev.0 (rust)";
```

- [ ] **Step 5: Implement the Clap parser**

Create `implementations/rust/src/cli.rs`:

```rust
use clap::Parser;

use crate::build_info;

#[derive(Debug, Parser)]
#[command(
    name = "polytui",
    about = "Learn CLI/TUI development across four languages",
    version = build_info::VERSION_TEXT
)]
pub struct Cli {}
```

- [ ] **Step 6: Add the Rust executable**

Replace `implementations/rust/src/main.rs` with:

```rust
use clap::Parser;
use polytui::cli::Cli;

fn main() {
    Cli::parse();
}
```

- [ ] **Step 7: Format and run the Rust tests**

Run:

```bash
cd implementations/rust
cargo fmt --check
cargo test --locked
```

Expected: PASS.

- [ ] **Step 8: Verify the Rust CLI**

Run:

```bash
cd implementations/rust
cargo run --quiet -- --version
```

Expected:

```text
polytui 0.1.0-dev.0 (rust)
```

- [ ] **Step 9: Commit the Rust entry point**

```bash
git add implementations/rust
git commit -m "feat(rust): add polytui CLI entry point"
```

---

### Task 4: TypeScript CLI Entry Point

**Files:**
- Create: `implementations/typescript/package.json`
- Create: `implementations/typescript/pnpm-lock.yaml`
- Create: `implementations/typescript/tsconfig.json`
- Create: `implementations/typescript/src/build-info.ts`
- Create: `implementations/typescript/src/cli.ts`
- Create: `implementations/typescript/src/index.ts`
- Create: `implementations/typescript/test/cli.test.ts`

**Interfaces:**
- Consumes: root version value `0.1.0-dev.0`.
- Produces: `versionText`; `createProgram(): Command`; `pnpm run dev -- --version` prints `polytui 0.1.0-dev.0 (typescript)`.

- [ ] **Step 1: Initialize the pnpm package**

Create `implementations/typescript/package.json`:

```json
{
  "name": "@polytui/typescript",
  "version": "0.1.0-dev.0",
  "private": true,
  "type": "module",
  "bin": {
    "polytui": "./dist/src/index.js"
  },
  "scripts": {
    "build": "tsc -p tsconfig.json",
    "dev": "tsx src/index.ts",
    "test": "vitest run",
    "typecheck": "tsc -p tsconfig.json --noEmit"
  },
  "engines": {
    "node": ">=24.15.0"
  }
}
```

Install dependencies:

```bash
cd implementations/typescript
pnpm add commander@15.0.0
pnpm add -D typescript@7.0.2 tsx@4.23.1 vitest@4.1.10 @types/node@26.1.1
```

Expected: `pnpm-lock.yaml` is created.

- [ ] **Step 2: Add the TypeScript compiler configuration**

Create `implementations/typescript/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2024",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "rootDir": ".",
    "outDir": "dist",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts", "test/**/*.ts"]
}
```

- [ ] **Step 3: Write the failing TypeScript CLI test**

Create `implementations/typescript/test/cli.test.ts`:

```ts
import {describe, expect, it} from 'vitest';

import {createProgram} from '../src/cli.js';

describe('createProgram', () => {
  it('uses the shared version text', () => {
    expect(createProgram().version()).toBe(
      'polytui 0.1.0-dev.0 (typescript)',
    );
  });
});
```

- [ ] **Step 4: Run the TypeScript test to verify it fails**

Run:

```bash
cd implementations/typescript
pnpm test
```

Expected: FAIL because `src/cli.ts` does not exist.

- [ ] **Step 5: Add TypeScript build identity**

Create `implementations/typescript/src/build-info.ts`:

```ts
export const version = '0.1.0-dev.0';
export const language = 'typescript';
export const versionText = `polytui ${version} (${language})`;
```

- [ ] **Step 6: Implement the Commander program**

Create `implementations/typescript/src/cli.ts`:

```ts
import {Command} from 'commander';

import {versionText} from './build-info.js';

export function createProgram(): Command {
  return new Command()
    .name('polytui')
    .description('Learn CLI/TUI development across four languages')
    .version(versionText);
}
```

- [ ] **Step 7: Add the TypeScript executable**

Create `implementations/typescript/src/index.ts`:

```ts
#!/usr/bin/env node

import {createProgram} from './cli.js';

await createProgram().parseAsync(process.argv);
```

- [ ] **Step 8: Run TypeScript tests and build**

Run:

```bash
cd implementations/typescript
pnpm test
pnpm run typecheck
pnpm run build
```

Expected: all commands exit `0`.

- [ ] **Step 9: Verify the TypeScript CLI**

Run:

```bash
cd implementations/typescript
pnpm run dev -- --version
```

Expected:

```text
polytui 0.1.0-dev.0 (typescript)
```

- [ ] **Step 10: Commit the TypeScript entry point**

```bash
git add implementations/typescript
git commit -m "feat(typescript): add polytui CLI entry point"
```

---

### Task 5: Python CLI Entry Point Managed by uv

**Files:**
- Create: `implementations/python/pyproject.toml`
- Create: `implementations/python/uv.lock`
- Create: `implementations/python/src/polytui/__init__.py`
- Create: `implementations/python/src/polytui/__main__.py`
- Create: `implementations/python/src/polytui/build_info.py`
- Create: `implementations/python/src/polytui/cli.py`
- Create: `implementations/python/tests/test_cli.py`

**Interfaces:**
- Consumes: root SemVer `0.1.0-dev.0`; Python metadata equivalent `0.1.0.dev0`.
- Produces: `VERSION_TEXT`; Typer `app`; `uv run polytui --version` prints `polytui 0.1.0-dev.0 (python)`.

- [ ] **Step 1: Initialize the uv package**

Run:

```bash
uv init --package --python 3.13 implementations/python
uv add --project implementations/python "typer==0.27.0"
uv add --project implementations/python --dev "pytest==9.1.1"
```

Expected: `implementations/python/pyproject.toml`, `uv.lock`, and `src/polytui/__init__.py` exist.

- [ ] **Step 2: Set the Python metadata and script entry point**

Ensure `implementations/python/pyproject.toml` contains these project fields while preserving the exact dependency versions written by uv:

```toml
[project]
name = "polytui"
version = "0.1.0.dev0"
description = "Python implementation of the PolyTUI learning project"
requires-python = ">=3.13"
dependencies = [
    "typer==0.27.0",
]

[project.scripts]
polytui = "polytui.cli:app"
```

Keep the uv-created build-system section and the uv-managed development dependency group containing pytest.
The development group must contain exactly `pytest==9.1.1` at this slice.

- [ ] **Step 3: Write the failing Python CLI test**

Create `implementations/python/tests/test_cli.py`:

```python
from typer.testing import CliRunner

from polytui.cli import app

runner = CliRunner()


def test_version_flag_uses_shared_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == "polytui 0.1.0-dev.0 (python)\n"
```

- [ ] **Step 4: Run the Python test to verify it fails**

Run:

```bash
uv run --project implementations/python pytest -q
```

Expected: FAIL because `polytui.cli` does not exist.

- [ ] **Step 5: Add Python build identity**

Create `implementations/python/src/polytui/build_info.py`:

```python
VERSION = "0.1.0-dev.0"
LANGUAGE = "python"
VERSION_TEXT = f"polytui {VERSION} ({LANGUAGE})"
```

- [ ] **Step 6: Implement the Typer application**

Create `implementations/python/src/polytui/cli.py`:

```python
from typing import Annotated

import typer

from polytui.build_info import VERSION_TEXT

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Learn CLI/TUI development across four languages.",
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(VERSION_TEXT)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    del version
```

- [ ] **Step 7: Add the Python module entry point**

Create `implementations/python/src/polytui/__main__.py`:

```python
from polytui.cli import app

app()
```

Keep `implementations/python/src/polytui/__init__.py` empty.

- [ ] **Step 8: Sync and run the Python tests**

Run:

```bash
uv sync --project implementations/python
uv run --project implementations/python pytest -q
```

Expected: PASS.

- [ ] **Step 9: Verify both Python entry points**

Run:

```bash
uv run --project implementations/python polytui --version
uv run --project implementations/python python -m polytui --version
```

Expected from each command:

```text
polytui 0.1.0-dev.0 (python)
```

- [ ] **Step 10: Verify prohibited Python project files do not exist**

Run:

```bash
find implementations/python -maxdepth 2 \
  \( -name requirements.txt -o -name Pipfile -o -name poetry.lock \) \
  -print
```

Expected: no output.

- [ ] **Step 11: Commit the uv-managed Python entry point**

```bash
git add implementations/python
git commit -m "feat(python): add uv-managed polytui CLI"
```

---

### Task 6: Root Version Parity and Developer Commands

**Files:**
- Create: `scripts/check-versions.sh`
- Create: `Makefile`

**Interfaces:**
- Consumes: all four CLI entry points and root `VERSION`.
- Produces: `scripts/check-versions.sh`; root targets `contracts`, `test-go`, `test-rust`, `test-typescript`, `test-python`, `versions`, and `test`.

- [ ] **Step 1: Write a failing version parity script**

Create `scripts/check-versions.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
version="$(tr -d '\n' < "${repo_root}/VERSION")"

check_version() {
  local language="$1"
  local expected="polytui ${version} (${language})"
  shift

  local actual
  actual="$("$@")"
  if [[ "${actual}" != "${expected}" ]]; then
    printf 'version mismatch for %s\nexpected: %s\nactual:   %s\n' \
      "${language}" "${expected}" "${actual}" >&2
    return 1
  fi
}

check_version go \
  bash -c "cd '${repo_root}/implementations/go' && go run ./cmd/polytui --version"
check_version rust \
  cargo run --quiet --locked \
    --manifest-path "${repo_root}/implementations/rust/Cargo.toml" \
    -- --version
check_version typescript \
  pnpm --dir "${repo_root}/implementations/typescript" \
    exec tsx src/index.ts --version
check_version python \
  uv run --project "${repo_root}/implementations/python" \
    polytui --version

printf 'all implementations report %s\n' "${version}"
```

Mark it executable:

```bash
chmod +x scripts/check-versions.sh
```

- [ ] **Step 2: Temporarily change the Go version to prove parity fails**

Change `implementations/go/internal/buildinfo/buildinfo.go` so `Version` is temporarily:

```go
Version = "0.1.0-broken"
```

Run:

```bash
./scripts/check-versions.sh
```

Expected: exit code `1` with `version mismatch for go`.

- [ ] **Step 3: Restore the Go version and verify parity passes**

Restore:

```go
Version = "0.1.0-dev.0"
```

Run:

```bash
./scripts/check-versions.sh
```

Expected:

```text
all implementations report 0.1.0-dev.0
```

- [ ] **Step 4: Add root Make targets**

Create `Makefile`:

```make
.PHONY: contracts test-go test-rust test-typescript test-python versions test

contracts:
	./scripts/validate-contracts.sh

test-go:
	cd implementations/go && go test ./...

test-rust:
	cargo fmt --check --manifest-path implementations/rust/Cargo.toml
	cargo test --locked --manifest-path implementations/rust/Cargo.toml

test-typescript:
	pnpm --dir implementations/typescript test
	pnpm --dir implementations/typescript run typecheck
	pnpm --dir implementations/typescript run build

test-python:
	uv sync --frozen --project implementations/python
	uv run --project implementations/python pytest -q

versions:
	./scripts/check-versions.sh

test: contracts test-go test-rust test-typescript test-python versions
```

- [ ] **Step 5: Run the root test entry point**

Run:

```bash
make test
```

Expected: every target passes and the final output includes `all implementations report 0.1.0-dev.0`.

- [ ] **Step 6: Commit root orchestration**

```bash
git add Makefile scripts/check-versions.sh
git commit -m "build: add synchronized root checks"
```

---

### Task 7: Documentation and Six macOS CI Gates

**Files:**
- Create: `README.md`
- Create: `CHANGELOG.md`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: all commands produced by Tasks 1-6.
- Produces: contributor documentation and required checks named `validate-contracts`, `test-go-macos`, `test-rust-macos`, `test-typescript-macos`, `test-python-macos-uv`, and `blackbox-parity-macos`.

- [ ] **Step 1: Write the contributor README**

Create `README.md`:

````markdown
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
````

- [ ] **Step 2: Start the synchronized changelog**

Create `CHANGELOG.md`:

```markdown
# Changelog

All notable changes to PolyTUI are recorded here. The four implementations use
one synchronized version.

## [Unreleased]

### Added

- Versioned deterministic stream scenario contract.
- Independent Go, Rust, TypeScript, and uv-managed Python CLI entry points.
- Root contract, test, build, and version parity commands.
- macOS continuous integration for all four implementations.
```

- [ ] **Step 3: Add the six-job macOS workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: ci

on:
  pull_request:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  validate-contracts:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          version: "0.8.9"
      - run: ./scripts/validate-contracts.sh

  test-go-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version: "1.26.5"
          cache-dependency-path: implementations/go/go.sum
      - run: go test ./...
        working-directory: implementations/go

  test-rust-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: "1.97.1"
          components: rustfmt
      - run: cargo fmt --check
        working-directory: implementations/rust
      - run: cargo test --locked
        working-directory: implementations/rust

  test-typescript-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: "10.33.2"
      - uses: actions/setup-node@v4
        with:
          node-version: "24.15.0"
          cache: pnpm
          cache-dependency-path: implementations/typescript/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
        working-directory: implementations/typescript
      - run: pnpm test
        working-directory: implementations/typescript
      - run: pnpm run typecheck
        working-directory: implementations/typescript
      - run: pnpm run build
        working-directory: implementations/typescript

  test-python-macos-uv:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          version: "0.8.9"
          python-version: "3.13.14"
          enable-cache: true
          cache-dependency-glob: implementations/python/uv.lock
      - run: uv sync --frozen
        working-directory: implementations/python
      - run: uv run pytest -q
        working-directory: implementations/python

  blackbox-parity-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version: "1.26.5"
          cache-dependency-path: implementations/go/go.sum
      - uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: "1.97.1"
      - uses: pnpm/action-setup@v4
        with:
          version: "10.33.2"
      - uses: actions/setup-node@v4
        with:
          node-version: "24.15.0"
          cache: pnpm
          cache-dependency-path: implementations/typescript/pnpm-lock.yaml
      - uses: astral-sh/setup-uv@v7
        with:
          version: "0.8.9"
          python-version: "3.13.14"
          enable-cache: true
          cache-dependency-glob: implementations/python/uv.lock
      - run: pnpm install --frozen-lockfile
        working-directory: implementations/typescript
      - run: uv sync --frozen
        working-directory: implementations/python
      - run: ./scripts/check-versions.sh
```

- [ ] **Step 4: Validate workflow syntax and local checks**

Run:

```bash
make test
git diff --check
```

Expected: `make test` passes and `git diff --check` prints no output.

- [ ] **Step 5: Inspect the complete slice**

Run:

```bash
git status --short
git diff --stat
```

Expected: only `README.md`, `CHANGELOG.md`, and `.github/workflows/ci.yml` are uncommitted at this task boundary; `AGENTS.md` remains untracked and unchanged.

- [ ] **Step 6: Commit documentation and CI**

```bash
git add README.md CHANGELOG.md .github/workflows/ci.yml
git commit -m "ci: add macOS monorepo quality gates"
```

- [ ] **Step 7: Run final slice verification**

Run:

```bash
make test
git status --short
git log --oneline --decorate -7
```

Expected:

- `make test` passes;
- `git status --short` reports only `?? AGENTS.md`;
- the log contains one commit for contracts, each language, root orchestration, and CI;
- no `v0.1.0` tag is created because M1 is not complete.

---

## Slice 1 Acceptance Checklist

- [ ] `VERSION` contains `0.1.0-dev.0`.
- [ ] `./scripts/validate-contracts.sh` validates every shared scenario.
- [ ] Go prints `polytui 0.1.0-dev.0 (go)`.
- [ ] Rust prints `polytui 0.1.0-dev.0 (rust)`.
- [ ] TypeScript prints `polytui 0.1.0-dev.0 (typescript)`.
- [ ] Python prints `polytui 0.1.0-dev.0 (python)`.
- [ ] Python uses uv and commits `uv.lock`.
- [ ] `make test` passes on macOS.
- [ ] `.github/workflows/ci.yml` declares all six required check names.
- [ ] No TUI framework, network client, model integration, session storage, or agent tool is added.
- [ ] `AGENTS.md` remains unchanged and untracked.
