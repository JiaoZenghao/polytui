# M1 TUI Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every no-argument PolyTUI implementation open the same minimal inline startup view, reject non-TTY interactive launches, exit through `Ctrl+C` or `Ctrl+D`, and restore the macOS terminal reliably.

**Architecture:** A shared JSON lifecycle contract defines exact visible text, diagnostics, exit codes, and bypass behavior. Each language keeps its CLI parser, adds a small injected interactive runner, and delegates terminal mutation to its native framework. Root-level non-TTY and PTY black-box tests enforce parity without comparing framework-specific ANSI bytes.

**Tech Stack:** Go 1.26.5, Bubble Tea v2.0.8, x/term v0.45.0, Rust 1.97.1, Ratatui 0.30.2, Crossterm 0.29.0, Node.js 24.15.0, pnpm 10.33.2, Ink 7.1.1, React 19.2.8, Python 3.13.14, uv 0.8.9, Textual 8.2.8, pytest 9.1.1, pytest-asyncio 1.4.0, macOS PTY/termios.

## Global Constraints

- Implement Go, Rust, TypeScript, and Python in the same slice.
- Support macOS only.
- Render exactly `PolyTUI · <Language>` followed by `Press Ctrl+C or Ctrl+D to exit`.
- Use labels `Go`, `Rust`, `TypeScript`, and `Python`.
- Use inline mode and never enter the alternate screen.
- Preserve the startup view in terminal scrollback after exit.
- Require both `stdin` and `stdout` to be TTYs only for no-argument interactive mode.
- Keep `--version` and `--help` successful without a TTY.
- Emit exactly `polytui: interactive mode requires a TTY` on `stderr` and exit `2` for non-TTY interactive mode.
- Emit exactly `polytui: interactive mode failed` on `stderr` and exit `1` for unexpected interactive failures.
- Exit `0` for both `Ctrl+C` and `Ctrl+D`.
- Ignore other input in this slice.
- Manage Python exclusively with uv and commit `uv.lock`.
- Keep existing artifact formats, upload policy, run targets, and version output unchanged.
- Do not add editing, submission, streaming, cancellation, resize, model, network, or tool behavior.

---

## File Map

- `contracts/schema/lifecycle.schema.json`: portable lifecycle-contract schema.
- `contracts/lifecycle/startup.json`: exact shared startup behavior.
- `scripts/validate-contracts.sh`: validates scenario and lifecycle contracts.
- `implementations/go/internal/tui/model.go`: Bubble Tea startup model.
- `implementations/go/internal/tui/runner.go`: Go TTY preflight and framework adapter.
- `implementations/go/internal/cli/root.go`: Cobra action and exit-code mapping.
- `implementations/rust/src/app.rs`: Rust TTY preflight and process outcome.
- `implementations/rust/src/tui.rs`: Ratatui inline renderer and event loop.
- `implementations/typescript/src/app.tsx`: Ink startup component.
- `implementations/typescript/src/terminal.tsx`: TypeScript preflight and Ink adapter.
- `implementations/python/src/polytui/app.py`: Textual startup application.
- `implementations/python/src/polytui/terminal.py`: Python preflight and Textual adapter.
- `scripts/test-tui-non-tty.sh`: four-language non-TTY black-box test.
- `scripts/test-tui-lifecycle.py`: eight-scenario macOS PTY lifecycle test.
- `Makefile`: root lifecycle targets and aggregate test.
- `.github/workflows/ci.yml`: runs lifecycle tests in the provisioned parity job.
- `scripts/validate-ci-artifacts.sh`: requires lifecycle regression execution in CI.
- `scripts/test-ci-artifacts-policy.sh`: proves removal of either lifecycle CI
  invocation is rejected.
- `README.md`: documents the now-interactive slice.

### Task 1: Shared lifecycle contract

**Files:**
- Create: `contracts/schema/lifecycle.schema.json`
- Create: `contracts/lifecycle/startup.json`
- Modify: `scripts/validate-contracts.sh`

**Interfaces:**
- Produces: exact banner labels, hint, diagnostics, exit codes, exit keys, and CLI bypass flags consumed by all later tasks.
- Verifies: `./scripts/validate-contracts.sh`.

- [ ] **Step 1: Make contract validation reference the missing lifecycle files**

Append this command to `scripts/validate-contracts.sh`:

```sh
uvx --from check-jsonschema==0.37.4 \
  check-jsonschema \
  --schemafile contracts/schema/lifecycle.schema.json \
  contracts/lifecycle/*.json
```

- [ ] **Step 2: Verify RED**

Run:

```sh
./scripts/validate-contracts.sh
```

Expected: non-zero because `contracts/schema/lifecycle.schema.json` and
`contracts/lifecycle/*.json` do not exist.

- [ ] **Step 3: Add the lifecycle schema**

Create `contracts/schema/lifecycle.schema.json` with:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/JiaoZenghao/polytui/contracts/schema/lifecycle.schema.json",
  "title": "PolyTUI interactive lifecycle contract",
  "type": "object",
  "required": [
    "format_version",
    "banners",
    "exit_hint",
    "diagnostics",
    "exit_codes",
    "exit_keys",
    "non_tty_bypass"
  ],
  "properties": {
    "format_version": { "const": 1 },
    "banners": {
      "type": "object",
      "required": ["go", "rust", "typescript", "python"],
      "properties": {
        "go": { "const": "PolyTUI · Go" },
        "rust": { "const": "PolyTUI · Rust" },
        "typescript": { "const": "PolyTUI · TypeScript" },
        "python": { "const": "PolyTUI · Python" }
      },
      "additionalProperties": false
    },
    "exit_hint": { "const": "Press Ctrl+C or Ctrl+D to exit" },
    "diagnostics": {
      "type": "object",
      "required": ["non_tty", "internal"],
      "properties": {
        "non_tty": { "const": "polytui: interactive mode requires a TTY" },
        "internal": { "const": "polytui: interactive mode failed" }
      },
      "additionalProperties": false
    },
    "exit_codes": {
      "type": "object",
      "required": ["success", "internal", "non_tty"],
      "properties": {
        "success": { "const": 0 },
        "internal": { "const": 1 },
        "non_tty": { "const": 2 }
      },
      "additionalProperties": false
    },
    "exit_keys": {
      "type": "array",
      "prefixItems": [
        { "const": "ctrl+c" },
        { "const": "ctrl+d" }
      ],
      "items": false,
      "minItems": 2,
      "maxItems": 2
    },
    "non_tty_bypass": {
      "type": "array",
      "prefixItems": [
        { "const": "--version" },
        { "const": "--help" }
      ],
      "items": false,
      "minItems": 2,
      "maxItems": 2
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 4: Add the exact lifecycle instance**

Create `contracts/lifecycle/startup.json`:

```json
{
  "format_version": 1,
  "banners": {
    "go": "PolyTUI · Go",
    "rust": "PolyTUI · Rust",
    "typescript": "PolyTUI · TypeScript",
    "python": "PolyTUI · Python"
  },
  "exit_hint": "Press Ctrl+C or Ctrl+D to exit",
  "diagnostics": {
    "non_tty": "polytui: interactive mode requires a TTY",
    "internal": "polytui: interactive mode failed"
  },
  "exit_codes": {
    "success": 0,
    "internal": 1,
    "non_tty": 2
  },
  "exit_keys": ["ctrl+c", "ctrl+d"],
  "non_tty_bypass": ["--version", "--help"]
}
```

- [ ] **Step 5: Verify GREEN**

Run:

```sh
./scripts/validate-contracts.sh
git diff --check
```

Expected: both schema validations pass and Git reports no whitespace errors.

- [ ] **Step 6: Commit**

```sh
git add contracts/schema/lifecycle.schema.json contracts/lifecycle/startup.json scripts/validate-contracts.sh
git commit -m "test: define TUI lifecycle contract"
```

### Task 2: Go inline startup lifecycle

**Files:**
- Modify: `implementations/go/go.mod`
- Modify: `implementations/go/go.sum`
- Modify: `implementations/go/internal/cli/root.go`
- Modify: `implementations/go/internal/cli/root_test.go`
- Modify: `implementations/go/cmd/polytui/main.go`
- Create: `implementations/go/internal/tui/model.go`
- Create: `implementations/go/internal/tui/model_test.go`
- Create: `implementations/go/internal/tui/runner.go`
- Create: `implementations/go/internal/tui/runner_test.go`

**Interfaces:**
- Consumes: banner, hint, diagnostics, and exit codes from Task 1.
- Produces: `cli.Execute(args, stdout, stderr, runInteractive) int`.
- Produces: `tui.NewRunner(stdin, stdout).Run() error`.

- [ ] **Step 1: Add failing CLI action tests**

Change the constructor signature to be tested as:

```go
func NewRootCommand(runInteractive func() error) *cobra.Command
```

Add tests that:

```go
func TestDefaultActionRunsInteractiveOnce(t *testing.T) {
    calls := 0
    command := NewRootCommand(func() error {
        calls++
        return nil
    })
    command.SetArgs(nil)
    if err := command.Execute(); err != nil {
        t.Fatal(err)
    }
    if calls != 1 {
        t.Fatalf("calls = %d, want 1", calls)
    }
}

func TestVersionAndHelpBypassInteractive(t *testing.T) {
    for _, args := range [][]string{{"--version"}, {"--help"}} {
        calls := 0
        command := NewRootCommand(func() error {
            calls++
            return nil
        })
        command.SetArgs(args)
        command.SetOut(&bytes.Buffer{})
        if err := command.Execute(); err != nil {
            t.Fatal(err)
        }
        if calls != 0 {
            t.Fatalf("%v called interactive runner %d time(s)", args, calls)
        }
    }
}
```

Update the existing version test to pass a runner that fails the test if
called.

- [ ] **Step 2: Verify CLI RED**

Run:

```sh
cd implementations/go
go test ./internal/cli
```

Expected: compile failure because `NewRootCommand` does not accept the runner
and no default action exists.

- [ ] **Step 3: Add dependencies and the minimal Bubble Tea model tests**

Run:

```sh
cd implementations/go
go get charm.land/bubbletea/v2@v2.0.8
go get golang.org/x/term@v0.45.0
```

Create `internal/tui/model_test.go` using:

```go
func TestModelView(t *testing.T) {
    got := newModel().View().Content
    want := "PolyTUI · Go\nPress Ctrl+C or Ctrl+D to exit"
    if got != want {
        t.Fatalf("View() = %q, want %q", got, want)
    }
}

func TestModelExitKeys(t *testing.T) {
    for _, key := range []rune{'c', 'd'} {
        _, command := newModel().Update(tea.KeyPressMsg(tea.Key{
            Code: key,
            Mod:  tea.ModCtrl,
        }))
        if command == nil {
            t.Fatalf("ctrl+%c did not request exit", key)
        }
        if _, ok := command().(tea.QuitMsg); !ok {
            t.Fatalf("ctrl+%c command did not return QuitMsg", key)
        }
    }
}

func TestModelIgnoresOtherKeys(t *testing.T) {
    _, command := newModel().Update(tea.KeyPressMsg(tea.Key{Code: 'x'}))
    if command != nil {
        t.Fatal("ordinary key requested an effect")
    }
}
```

- [ ] **Step 4: Verify model RED**

Run:

```sh
go test ./internal/tui
```

Expected: compile failure because `newModel` does not exist.

- [ ] **Step 5: Implement the Bubble Tea model**

Create `internal/tui/model.go` with these exact semantics:

```go
package tui

import tea "charm.land/bubbletea/v2"

const (
    Banner   = "PolyTUI · Go"
    ExitHint = "Press Ctrl+C or Ctrl+D to exit"
)

type model struct{}

func newModel() model { return model{} }
func (model) Init() tea.Cmd { return nil }

func (m model) Update(message tea.Msg) (tea.Model, tea.Cmd) {
    if key, ok := message.(tea.KeyPressMsg); ok {
        switch key.Keystroke() {
        case "ctrl+c", "ctrl+d":
            return m, tea.Quit
        }
    }
    return m, nil
}

func (model) View() tea.View {
    return tea.NewView(Banner + "\n" + ExitHint)
}
```

Use Bubble Tea's default inline mode; do not add an alternate-screen option.

- [ ] **Step 6: Add failing runner and exit-code tests**

Define tests around these production seams:

```go
var ErrNotTTY = errors.New("interactive mode requires a TTY")

type ProgramRunner func(tea.Model, ...tea.ProgramOption) (tea.Model, error)

type Runner struct {
    stdin      *os.File
    stdout     *os.File
    isTerminal func(int) bool
    runProgram ProgramRunner
}
```

Test:

- either false TTY predicate returns `ErrNotTTY` and never calls
  `runProgram`;
- both true predicates call `runProgram` once;
- a program error is returned unchanged.

Add `cli.Execute` table tests:

```go
{
    name: "success",
    run: func() error { return nil },
    wantCode: 0,
    wantErr: "",
},
{
    name: "non tty",
    run: func() error { return tui.ErrNotTTY },
    wantCode: 2,
    wantErr: "polytui: interactive mode requires a TTY\n",
},
{
    name: "internal",
    run: func() error { return errors.New("boom") },
    wantCode: 1,
    wantErr: "polytui: interactive mode failed\n",
},
```

- [ ] **Step 7: Verify runner RED**

Run:

```sh
go test ./internal/tui ./internal/cli
```

Expected: compile failures for the missing runner and `cli.Execute`.

- [ ] **Step 8: Implement runner, CLI mapping, and main**

Implement `Runner.Run`:

```go
func (runner Runner) Run() error {
    if !runner.isTerminal(int(runner.stdin.Fd())) ||
        !runner.isTerminal(int(runner.stdout.Fd())) {
        return ErrNotTTY
    }
    _, err := runner.runProgram(
        newModel(),
        tea.WithInput(runner.stdin),
        tea.WithOutput(runner.stdout),
    )
    return err
}
```

`NewRunner` supplies `term.IsTerminal` and a `tea.NewProgram(...).Run()`
adapter.

Set Cobra's `RunE` to `runInteractive`. Implement:

```go
func Execute(
    args []string,
    stdout io.Writer,
    stderr io.Writer,
    runInteractive func() error,
) int
```

It sets command args/output/error, executes once, emits only the two exact
contract diagnostics, and returns `0`, `1`, or `2`. Use `errors.Is` for
`tui.ErrNotTTY`.

Change `main.go` to:

```go
runner := tui.NewRunner(os.Stdin, os.Stdout)
os.Exit(cli.Execute(os.Args[1:], os.Stdout, os.Stderr, runner.Run))
```

- [ ] **Step 9: Verify Go GREEN**

Run:

```sh
cd implementations/go
gofmt -w cmd internal
go test ./...
go run ./cmd/polytui --version
go run ./cmd/polytui </dev/null
```

Expected: tests pass; version remains exact; the last command exits `2` with
only the non-TTY diagnostic.

- [ ] **Step 10: Commit**

```sh
git add implementations/go
git commit -m "feat(go): add inline TUI lifecycle"
```

### Task 3: Rust inline startup lifecycle

**Files:**
- Modify: `implementations/rust/Cargo.toml`
- Modify: `implementations/rust/Cargo.lock`
- Modify: `implementations/rust/src/lib.rs`
- Modify: `implementations/rust/src/main.rs`
- Create: `implementations/rust/src/app.rs`
- Create: `implementations/rust/src/tui.rs`

**Interfaces:**
- Consumes: Task 1 contract values.
- Produces: `app::run_with(runtime: &mut dyn Runtime) -> Outcome`.
- Produces: `tui::run() -> std::io::Result<()>`.

- [ ] **Step 1: Add dependencies**

Update dependencies:

```toml
ratatui = { version = "0.30.2", features = ["crossterm_0_29"] }
crossterm = "0.29.0"
```

Run:

```sh
cargo update --manifest-path implementations/rust/Cargo.toml
```

- [ ] **Step 2: Write failing outcome and runtime tests**

Create `src/app.rs` tests around:

```rust
pub const NON_TTY_DIAGNOSTIC: &str =
    "polytui: interactive mode requires a TTY";
pub const INTERNAL_DIAGNOSTIC: &str =
    "polytui: interactive mode failed";

pub trait Runtime {
    fn stdin_is_terminal(&self) -> bool;
    fn stdout_is_terminal(&self) -> bool;
    fn run_tui(&mut self) -> std::io::Result<()>;
}

#[derive(Debug, Eq, PartialEq)]
pub enum Outcome {
    Success,
    NonTty,
    InternalFailure,
}
```

Use a fake runtime to assert:

- either false terminal predicate produces `Outcome::NonTty` without calling
  `run_tui`;
- both true predicates call `run_tui` once and produce `Success`;
- an I/O error produces `InternalFailure`.

- [ ] **Step 3: Write failing renderer and key tests**

In `src/tui.rs`, expose pure helpers:

```rust
pub const BANNER: &str = "PolyTUI · Rust";
pub const EXIT_HINT: &str = "Press Ctrl+C or Ctrl+D to exit";

pub fn is_exit_key(key: KeyEvent) -> bool;
pub fn render(frame: &mut Frame);
```

Tests must use `TestBackend` to assert the two visible lines, and construct:

```rust
KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)
KeyEvent::new(KeyCode::Char('d'), KeyModifiers::CONTROL)
```

Both are exits; plain `x` is not.

- [ ] **Step 4: Verify Rust RED**

Run:

```sh
cargo test --locked --manifest-path implementations/rust/Cargo.toml
```

Expected: compile failures for missing app/tui behavior.

- [ ] **Step 5: Implement app outcome mapping**

`run_with` must check both terminal predicates before calling the TUI:

```rust
pub fn run_with(runtime: &mut dyn Runtime) -> Outcome {
    if !runtime.stdin_is_terminal() || !runtime.stdout_is_terminal() {
        return Outcome::NonTty;
    }
    match runtime.run_tui() {
        Ok(()) => Outcome::Success,
        Err(_) => Outcome::InternalFailure,
    }
}
```

Implement `SystemRuntime` with `std::io::IsTerminal` and `tui::run`.

- [ ] **Step 6: Implement the Ratatui inline adapter**

Initialize with cleanup on partial failure:

```rust
let options = TerminalOptions {
    viewport: Viewport::Inline(2),
};
let mut terminal = match ratatui::try_init_with_options(options) {
    Ok(terminal) => terminal,
    Err(error) => {
        let _ = ratatui::try_restore();
        return Err(error);
    }
};
```

Draw a two-line `Paragraph`, read Crossterm events, and exit only when an
`Event::Key` has `KeyEventKind::Press` and `is_exit_key(key)` is true.

Always call `ratatui::try_restore()` after the loop. Preserve the first error:
if drawing or reading fails, attempt restoration and return the operation
error; if the operation succeeds but restoration fails, return the restoration
error. Do not call `ratatui::init()` or enter the alternate screen.

- [ ] **Step 7: Map outcomes in `main`**

Keep `Cli::parse()` before interactive startup. Then:

```rust
let mut runtime = SystemRuntime;
match run_with(&mut runtime) {
    Outcome::Success => ExitCode::SUCCESS,
    Outcome::NonTty => {
        eprintln!("{NON_TTY_DIAGNOSTIC}");
        ExitCode::from(2)
    }
    Outcome::InternalFailure => {
        eprintln!("{INTERNAL_DIAGNOSTIC}");
        ExitCode::from(1)
    }
}
```

Because Clap handles `--help` and `--version` during parsing, neither reaches
`run_with`.

- [ ] **Step 8: Verify Rust GREEN**

Run:

```sh
cargo fmt --check --manifest-path implementations/rust/Cargo.toml
cargo test --locked --manifest-path implementations/rust/Cargo.toml
cargo run --quiet --manifest-path implementations/rust/Cargo.toml -- --version
cargo run --quiet --manifest-path implementations/rust/Cargo.toml </dev/null
```

Expected: tests pass; version remains exact; non-TTY launch exits `2` with the
exact diagnostic.

- [ ] **Step 9: Commit**

```sh
git add implementations/rust
git commit -m "feat(rust): add inline TUI lifecycle"
```

### Task 4: TypeScript inline startup lifecycle

**Files:**
- Modify: `implementations/typescript/package.json`
- Modify: `implementations/typescript/pnpm-lock.yaml`
- Modify: `implementations/typescript/tsconfig.json`
- Modify: `implementations/typescript/tsconfig.test.json`
- Modify: `implementations/typescript/src/cli.ts`
- Modify: `implementations/typescript/src/index.ts`
- Modify: `implementations/typescript/test/cli.test.ts`
- Create: `implementations/typescript/src/app.tsx`
- Create: `implementations/typescript/src/terminal.tsx`
- Create: `implementations/typescript/test/app.test.tsx`
- Create: `implementations/typescript/test/terminal.test.tsx`

**Interfaces:**
- Consumes: Task 1 contract values.
- Produces: `createProgram(runInteractive?, setExitCode?)`.
- Produces: `runInteractive(streams?, renderApp?) -> Promise<number>`.

- [ ] **Step 1: Add exact dependencies and JSX configuration**

Run:

```sh
pnpm --dir implementations/typescript add ink@7.1.1 react@19.2.8
pnpm --dir implementations/typescript add -D @types/react@19.2.17 ink-testing-library@4.0.0
```

Add to compiler options:

```json
"jsx": "react-jsx"
```

Change both include globs to cover `*.tsx`.

- [ ] **Step 2: Write failing component tests**

Create `test/app.test.tsx`:

```tsx
import {render} from 'ink-testing-library';
import {describe, expect, it} from 'vitest';
import {StartupApp, isExitInput} from '../src/app.js';

it('renders the exact startup view', () => {
  const view = render(<StartupApp />);
  expect(view.lastFrame()).toBe(
    'PolyTUI · TypeScript\nPress Ctrl+C or Ctrl+D to exit',
  );
});

it.each(['c', 'd'])('accepts ctrl+%s', input => {
  expect(isExitInput(input, {ctrl: true})).toBe(true);
});

it('ignores ordinary input', () => {
  expect(isExitInput('x', {ctrl: false})).toBe(false);
});
```

Use a narrow `ExitKey` structural type containing only `ctrl: boolean` so the
pure helper is easy to test and compatible with Ink's input key object.

- [ ] **Step 3: Write failing terminal and CLI tests**

Test `runInteractive` with fake streams and an injected `renderApp`:

- non-TTY returns `2`, writes only the exact diagnostic, and never renders;
- injected renderer rejection returns `1` and writes only the internal
  diagnostic;
- successful `waitUntilExit` returns `0`.

Update CLI tests so injected `runInteractive` is called once for no args and
not called for `--version` or `--help`. Inject:

```ts
type SetExitCode = (code: number) => void;
```

and assert a non-zero result is handed to it.

- [ ] **Step 4: Verify TypeScript RED**

Run:

```sh
pnpm --dir implementations/typescript test
pnpm --dir implementations/typescript run typecheck
```

Expected: failures because `StartupApp`, `isExitInput`, `runInteractive`, and
the injected CLI action do not exist.

- [ ] **Step 5: Implement the Ink component**

Create `src/app.tsx`:

```tsx
import {Text, useApp, useInput} from 'ink';

export const banner = 'PolyTUI · TypeScript';
export const exitHint = 'Press Ctrl+C or Ctrl+D to exit';

export interface ExitKey {
  ctrl: boolean;
}

export function isExitInput(input: string, key: ExitKey): boolean {
  return key.ctrl && (input === 'c' || input === 'd');
}

export function StartupApp() {
  const {exit} = useApp();
  useInput((input, key) => {
    if (isExitInput(input, key)) {
      exit();
    }
  });
  return <Text>{`${banner}\n${exitHint}`}</Text>;
}
```

- [ ] **Step 6: Implement preflight and Ink rendering**

`src/terminal.tsx` defines stream interfaces with `isTTY` and `write`, checks
both required TTYs before rendering, and defaults to:

```tsx
render(<StartupApp />, {
  stdin: process.stdin,
  stdout: process.stdout,
  stderr: process.stderr,
  exitOnCtrlC: false,
  patchConsole: false,
});
```

Await `waitUntilExit()`. Catch framework errors, emit only the internal
diagnostic, and return the contract code.

- [ ] **Step 7: Implement the Commander action**

Change `createProgram` to accept:

```ts
export function createProgram(
  run: () => Promise<number> = runInteractive,
  setExitCode: (code: number) => void = code => {
    process.exitCode = code;
  },
): Command
```

Add an async default action that awaits `run()` and calls `setExitCode` only
when the result is non-zero. `index.ts` continues to await `parseAsync`.

- [ ] **Step 8: Verify TypeScript GREEN**

Run:

```sh
pnpm --dir implementations/typescript test
pnpm --dir implementations/typescript run typecheck
pnpm --dir implementations/typescript run build
pnpm --dir implementations/typescript exec tsx src/index.ts --version
pnpm --dir implementations/typescript exec tsx src/index.ts </dev/null
```

Expected: tests/typecheck/build pass; version remains exact; non-TTY launch
exits `2` with the exact diagnostic.

- [ ] **Step 9: Commit**

```sh
git add implementations/typescript
git commit -m "feat(typescript): add inline TUI lifecycle"
```

### Task 5: Python inline startup lifecycle

**Files:**
- Modify: `implementations/python/pyproject.toml`
- Modify: `implementations/python/uv.lock`
- Modify: `implementations/python/src/polytui/cli.py`
- Modify: `implementations/python/tests/test_cli.py`
- Create: `implementations/python/src/polytui/app.py`
- Create: `implementations/python/src/polytui/terminal.py`
- Create: `implementations/python/tests/test_app.py`
- Create: `implementations/python/tests/test_terminal.py`

**Interfaces:**
- Consumes: Task 1 contract values.
- Produces: `PolyTUIApp`.
- Produces: `run_interactive(stdin, stdout, stderr, app_factory) -> int`.

- [ ] **Step 1: Add exact uv-managed dependencies**

Run:

```sh
uv add --project implementations/python "textual==8.2.8"
uv add --project implementations/python --dev "pytest-asyncio==1.4.0"
```

Do not use pip or create another dependency file.

- [ ] **Step 2: Write failing Textual tests**

Create `tests/test_app.py`:

```python
import pytest
from textual.widgets import Static

from polytui.app import PolyTUIApp


@pytest.mark.asyncio
async def test_startup_view_and_ctrl_c() -> None:
    app = PolyTUIApp()
    async with app.run_test() as pilot:
        startup = app.query_one("#startup", Static)
        assert str(startup.renderable) == (
            "PolyTUI · Python\nPress Ctrl+C or Ctrl+D to exit"
        )
        await pilot.press("ctrl+c")
    assert app.return_value == 0


@pytest.mark.asyncio
async def test_ctrl_d_exits_successfully() -> None:
    app = PolyTUIApp()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+d")
    assert app.return_value == 0
```

- [ ] **Step 3: Write failing terminal and CLI tests**

Use fake text streams whose `isatty()` returns configured values. Test:

- either non-TTY stream returns `2`, does not construct the app, leaves stdout
  empty, and writes the exact diagnostic;
- an app factory or `run` exception returns `1` and writes the exact internal
  diagnostic;
- successful fake app returns `0`.

In `test_cli.py`, monkeypatch `polytui.cli.run_interactive` and assert:

- no args invoke it once and propagate exit code;
- `--version` and `--help` do not invoke it.

- [ ] **Step 4: Verify Python RED**

Run:

```sh
uv sync --project implementations/python
uv run --project implementations/python pytest -q
```

Expected: failures because the app and terminal modules do not exist and the
Typer callback does not invoke the runner.

- [ ] **Step 5: Implement the Textual app**

Create `src/polytui/app.py`:

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static


class PolyTUIApp(App[int]):
    INLINE_PADDING = 0
    CSS = """
    Screen {
        height: 2;
    }
    #startup {
        height: 2;
    }
    """
    BINDINGS = [
        Binding("ctrl+c", "exit_success", show=False, priority=True),
        Binding("ctrl+d", "exit_success", show=False, priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            "PolyTUI · Python\nPress Ctrl+C or Ctrl+D to exit",
            id="startup",
        )

    def action_exit_success(self) -> None:
        self.exit(result=0, return_code=0)
```

- [ ] **Step 6: Implement terminal preflight**

Create `terminal.py` with exact constants and:

```python
def run_interactive(
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    app_factory: Callable[[], PolyTUIApp] = PolyTUIApp,
) -> int:
```

Check `stdin.isatty()` and `stdout.isatty()` before constructing the app.
Run:

```python
result = app_factory().run(
    inline=True,
    inline_no_clear=True,
    mouse=False,
)
return int(result or 0)
```

Catch unexpected exceptions, emit only the internal diagnostic, and return
`1`.

- [ ] **Step 7: Wire the Typer callback**

After the eager version option has been processed, call `run_interactive()`.
If its result is non-zero, raise `typer.Exit(code=result)`. Do not catch
Typer's help/version exits or perform TTY checks before the callback.

- [ ] **Step 8: Verify Python GREEN**

Run:

```sh
uv sync --frozen --project implementations/python
uv run --project implementations/python pytest -q
uv run --project implementations/python polytui --version
uv run --project implementations/python polytui </dev/null
```

Expected: tests pass; version remains exact; non-TTY launch exits `2` with the
exact diagnostic.

- [ ] **Step 9: Commit**

```sh
git add implementations/python
git commit -m "feat(python): add inline TUI lifecycle"
```

### Task 6: Shared non-TTY and macOS PTY lifecycle gates

**Files:**
- Create: `scripts/test-tui-non-tty.sh`
- Create: `scripts/test-tui-lifecycle.py`
- Modify: `Makefile`
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/validate-ci-artifacts.sh`
- Modify: `scripts/test-ci-artifacts-policy.sh`

**Interfaces:**
- Consumes: four direct application-entry commands and all four public
  `make run-<language>` targets.
- Produces: `make test-tui-non-tty` and `make test-tui-lifecycle`.
- Enforces: 4 exact application-entry non-TTY contracts, 4 public Make
  wrapper non-TTY contracts, 4 public-Make version bypasses, and 8 public-Make
  PTY exit scenarios.

- [ ] **Step 1: Add failing root targets**

Add to `.PHONY` and the aggregate `test` dependencies:

```make
test-tui-non-tty:
	./scripts/test-tui-non-tty.sh

test-tui-lifecycle:
	uv run --project implementations/python python scripts/test-tui-lifecycle.py
```

- [ ] **Step 2: Verify RED**

Run:

```sh
make test-tui-non-tty
make test-tui-lifecycle
```

Expected: both fail because their scripts do not exist.

- [ ] **Step 3: Implement the non-TTY shell test**

Create an executable POSIX shell script that uses `mktemp -d` and an exit trap.
Build the Go application into that temporary directory before the test loop;
this is the only build wrapper permitted for the strict application-entry
checks:

```sh
(cd implementations/go && go build -o "$tmp_dir/polytui-go" ./cmd/polytui)
```

Define a POSIX-shell dispatcher for the four direct application commands,
without Make:

```sh
run_application_entry() {
	case "$1" in
	go) "$tmp_dir/polytui-go" ;;
	rust) cargo run --quiet --manifest-path implementations/rust/Cargo.toml -- ;;
	typescript) pnpm --dir implementations/typescript exec tsx src/index.ts ;;
	python) uv run --project implementations/python polytui ;;
	esac
}
```

For each direct command, run it with `/dev/null` as input and separate captured
standard streams. Require the application contract exactly:

```sh
set +e
run_application_entry "$language" </dev/null >"$stdout_file" 2>"$stderr_file"
status=$?
set -e

test "$status" -eq 2
test ! -s "$stdout_file"
printf '%s\n' 'polytui: interactive mode requires a TTY' >"$expected_file"
cmp -s "$stderr_file" "$expected_file"
```

Do not call a Make target in this first loop: it validates application output,
so `stderr` must be exactly the single diagnostic line including its newline.

In a second loop, invoke each public `make --no-print-directory
run-<language>` target with the same redirected streams. Require status `2`,
empty `stdout`, and exactly one complete newline-terminated diagnostic line on
`stderr`. Capture `grep`'s count from `stdout` and compare the captured value
to `1`; `-x` makes the comparison a complete-line match rather than a
substring match:

```sh
set +e
diagnostic_count="$(grep -Fxc 'polytui: interactive mode requires a TTY' "$stderr_file")"
grep_status=$?
set -e
test "$grep_status" -eq 0
test "$diagnostic_count" -eq 1
last_stderr_byte="$(od -An -t x1 "$stderr_file" | awk '{ last = $NF } END { print last }')"
test "$last_stderr_byte" = 0a
```

Do not require the whole `stderr` file to match: Go's `go run` and GNU Make
may add wrapper diagnostics. `grep -Fxc` proves the diagnostic is a complete
line and occurs once. If that line is followed by wrapper output, its line
separator already proves the diagnostic newline; if it is the final line, the
`od`/`awk` assertion proves the complete `stderr` stream ends in byte `0a`.

In a third loop, invoke each public target with `ARGS="--version"` under the
same redirected streams. Require status `0`, empty `stderr`, and the existing
exact language-specific version line. This preserves public-target validation
for the scriptable bypass. Print one final success line only after all twelve
non-TTY checks pass.

- [ ] **Step 4: Implement the PTY harness**

Create `scripts/test-tui-lifecycle.py` using only the Python standard library.
Define:

```python
CASES = {
    "go": ("PolyTUI · Go", ["make", "run-go"]),
    "rust": ("PolyTUI · Rust", ["make", "run-rust"]),
    "typescript": ("PolyTUI · TypeScript", ["make", "run-typescript"]),
    "python": ("PolyTUI · Python", ["make", "run-python"]),
}
EXIT_KEYS = {"ctrl+c": b"\x03", "ctrl+d": b"\x04"}
EXIT_HINT = "Press Ctrl+C or Ctrl+D to exit"
```

For each of the eight cases:

- open a PTY with `pty.openpty()`;
- capture and normalize the complete `termios.tcgetattr(slave_fd)` value
  before launch (the first six fields plus every control character as an
  integer);
- set the actual slave terminal geometry before `Popen` with
  `fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))`;
  import `struct` for this `winsize` payload;
- start the command with all three standard streams attached to `slave_fd`;
- create a controlling terminal in the child with `os.setsid()` followed by
  `fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)`;
- close the parent's duplicate `slave_fd` immediately after `Popen`; this
  avoids holding the macOS controlling session open;
- set `TERM=xterm-256color`, `COLUMNS=80`, and `LINES=24`;
- read from `master_fd` with `select.select` until normalized output contains
  both expected lines;
- write the control byte;
- reap the child with `process.wait(timeout=TIMEOUT_SECONDS)` and require
  status `0` within five seconds; never use `os.kill(process.pid, 0)` as an
  exit test because it treats an unreaped zombie as running;
- drain remaining output with a deadline;
- while `master_fd` remains open, normalize and compare its complete
  `termios.tcgetattr(master_fd)` value with the original slave attributes;
- strip CSI/OSC sequences and require both lines remain in captured output.

On timeout, send `SIGTERM` to process group `Popen.pid`, wait one second while
continuing bounded PTY drains and cursor-position replies, send `SIGKILL` to
that group if needed, and require a second bounded `Popen.wait()` to reap the
top-level child. Raise a cleanup failure if reaping still times out. Close both
PTY file descriptors in `finally`. The harness continues to launch the public
Make commands shown in `CASES`, so all eight scenarios exercise the public
targets. Print `all TUI lifecycle PTY scenarios pass` only after all eight
cases pass.

- [ ] **Step 5: Verify shared tests GREEN**

Run from a real macOS terminal:

```sh
make test-tui-non-tty
make test-tui-lifecycle
```

Expected: all four direct application entries have exact non-TTY status,
stdout, and one-line `stderr` behavior; all four public Make targets have the
same status and empty stdout with the diagnostic exactly once; all four public
version targets pass; and all eight public-Make PTY cases pass with a real
80x24 PTY and reaped children.

- [ ] **Step 6: Wire CI and protect the invocation**

In `blackbox-parity-macos`, after `./scripts/test-run-targets.sh`, add:

```yaml
      - run: make test-tui-non-tty
      - run: make test-tui-lifecycle
```

In `scripts/validate-ci-artifacts.sh`, require both exact lines inside the
`blackbox-parity-macos` job:

```sh
assert_job_line blackbox-parity-macos "      - run: make test-tui-non-tty"
assert_job_line blackbox-parity-macos "      - run: make test-tui-lifecycle"
```

Add a `make_missing_line` fixture helper to
`scripts/test-ci-artifacts-policy.sh` that copies every workflow line except
one exact target:

```sh
make_missing_line() {
	output="$1"
	target="$2"
	awk -v target="$target" '$0 != target { print }' \
		"$base_workflow" >"$output"
}
```

Add two permanent rejected cases:

```sh
make_missing_line "$tmp_dir/missing-tui-non-tty.yml" \
	"      - run: make test-tui-non-tty"
expect_rejected missing-tui-non-tty \
	"$tmp_dir/missing-tui-non-tty.yml" \
	'blackbox-parity-macos: expected 1 exact line(s) "      - run: make test-tui-non-tty", found 0'

make_missing_line "$tmp_dir/missing-tui-lifecycle.yml" \
	"      - run: make test-tui-lifecycle"
expect_rejected missing-tui-lifecycle \
	"$tmp_dir/missing-tui-lifecycle.yml" \
	'blackbox-parity-macos: expected 1 exact line(s) "      - run: make test-tui-lifecycle", found 0'
```

- [ ] **Step 7: Run aggregate and policy tests**

Run:

```sh
make test
./scripts/test-ci-artifacts-policy.sh
git diff --check
```

Expected: all language, contract, artifact-policy, non-TTY, and PTY tests pass.

- [ ] **Step 8: Commit**

```sh
git add scripts/test-tui-non-tty.sh scripts/test-tui-lifecycle.py scripts/validate-ci-artifacts.sh scripts/test-ci-artifacts-policy.sh Makefile .github/workflows/ci.yml
git commit -m "test: enforce TUI lifecycle parity"
```

### Task 7: README and final branch verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: completed four-language startup lifecycle.
- Produces: contributor-facing run, TTY, exit, and scope documentation.

- [ ] **Step 1: Update current scope**

Replace the statement that the project does not start a TUI. State that the
current slice displays a minimal language-specific inline startup view,
supports clean `Ctrl+C`/`Ctrl+D` exit, and does not yet provide editing,
streaming, or model access.

- [ ] **Step 2: Document interactive commands**

Show:

```sh
make run-go
make run-rust
make run-typescript
make run-python
```

State that these commands require a real terminal. Keep the existing
`ARGS="--version"` examples and explain that `--version` and `--help` remain
usable from scripts and CI.

- [ ] **Step 3: Run final local verification**

Run:

```sh
make test
./scripts/test-native-artifact-archive.sh go TEST
./scripts/test-native-artifact-archive.sh rust TEST
git diff --check
git status --short
```

Expected: every test passes, native artifacts still execute, no whitespace
errors exist, and only `README.md` is uncommitted.

- [ ] **Step 4: Commit**

```sh
git add README.md
git commit -m "docs: explain minimal TUI lifecycle"
```

- [ ] **Step 5: Review the completed branch**

Run:

```sh
git log --oneline main..HEAD
git diff --stat main...HEAD
make test
```

Expected: the design, plan, and seven focused implementation commits are
present and the final suite exits `0`.

## Live GitHub Acceptance

After pushing the branch:

1. Confirm pull-request CI runs both lifecycle targets in
   `blackbox-parity-macos`.
2. Confirm all language jobs and the parity job pass.
3. Confirm artifact uploads remain skipped on the pull request.
4. Merge only after all checks pass.
5. Confirm the `main` workflow publishes the same four artifacts.
6. Download and run at least one native artifact in a macOS terminal; require
   the startup view and a clean exit.
