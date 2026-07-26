# M1 TUI Lifecycle Design

Date: 2026-07-26

## Purpose

Deliver the second M1 vertical slice in all four PolyTUI implementations. This
slice is the first interactive terminal experience: it shows a
language-specific inline startup view, validates the terminal before entering
interactive mode, exits cleanly through either supported control key, and
restores terminal state on every handled path.

The slice deliberately stops before text editing, message submission,
streaming, cancellation, or resize behavior. Those remain separate vertical
slices in the approved M1 design.

## Confirmed Product Decisions

- Keep Go, Rust, TypeScript, and Python behaviorally synchronized.
- Use each language's selected native TUI framework.
- Use a Codex-style inline interface and never enter the alternate screen.
- Show only a startup banner and exit hint; do not show an input prompt.
- Preserve the final startup view in terminal scrollback after exit.
- Require both standard input and standard output to be TTYs for interactive
  mode.
- Parse CLI arguments before TTY validation so `--version` and `--help` remain
  scriptable without a TTY.
- Treat `Ctrl+C` and `Ctrl+D` as successful exits in this slice.
- Continue to support macOS only.
- Continue to manage Python exclusively with uv.

## User-Visible Contract

Interactive startup renders exactly two semantic lines:

```text
PolyTUI · <Language>
Press Ctrl+C or Ctrl+D to exit
```

`<Language>` is exactly one of:

- `Go`
- `Rust`
- `TypeScript`
- `Python`

The visible text must survive normal exit in terminal scrollback. Framework
control sequences may differ, but normalized visible text, ordering, exit
behavior, and terminal restoration must match.

While the startup view is active:

- `Ctrl+C` exits successfully with status `0`.
- `Ctrl+D` exits successfully with status `0`.
- Other input does not produce user-visible business behavior.
- No input prompt, editable buffer, message, or streaming state is shown.

## CLI and TTY Behavior

CLI parsing happens before interactive startup:

- `polytui --version` prints the existing language-specific version and exits
  successfully without requiring a TTY.
- `polytui --help` prints CLI help and exits successfully without requiring a
  TTY.
- Running `polytui` without arguments attempts to start interactive mode.

Interactive mode requires both `stdin` and `stdout` to be TTYs. `stderr` does
not have to be a TTY.

When either required stream is not a TTY:

- no TUI framework is initialized;
- `stdout` remains empty;
- `stderr` receives exactly:

  ```text
  polytui: interactive mode requires a TTY
  ```

- the process exits with status `2`.

An unexpected framework, terminal, or I/O failure:

- attempts terminal restoration before returning;
- writes exactly `polytui: interactive mode failed` to `stderr`;
- does not display a stack trace by default;
- exits with status `1`.

## Shared Architecture

Each implementation uses the same conceptual path:

```text
CLI parser
  → no-argument interactive action
  → TTY preflight and exit-code mapping
  → framework adapter
  → inline startup view
  → Ctrl+C or Ctrl+D
  → framework cleanup and terminal restoration
  → successful process exit
```

The responsibilities remain separate:

1. **CLI layer** parses arguments and decides whether interactive mode should
   run.
2. **Interactive runner** checks TTY eligibility, owns error-to-exit-code
   mapping, and invokes an injected framework adapter.
3. **Framework adapter** renders the two-line startup view, recognizes the two
   exit keys, and uses framework-native lifecycle cleanup.
4. **Shared black-box tests** validate observable behavior without depending
   on framework-private ANSI output.

TTY validation must occur before the framework mutates terminal state. CLI
tests inject the interactive runner so `--version`, `--help`, default action,
and error mapping are independently testable.

## Language Implementations

### Go

- Keep Cobra as the CLI parser.
- Add Bubble Tea for the inline event loop.
- Do not use Bubble Tea's alternate-screen option.
- Use an explicit TTY predicate on `stdin` and `stdout`.
- Keep the Bubble Tea model limited to the banner, exit hint, and quit-key
  recognition.
- Use dependency injection at the Cobra action boundary so unit tests do not
  require a real terminal.
- Defer Lip Gloss styling until a slice needs width-aware presentation; this
  startup view does not need a styling dependency.

### Rust

- Keep Clap as the CLI parser.
- Use Ratatui with an inline viewport and Crossterm for terminal events.
- Do not call Ratatui initialization helpers that select fullscreen or the
  alternate screen.
- Use `std::io::IsTerminal` for preflight.
- Handle only key-press events for `Ctrl+C` and `Ctrl+D`.
- Make restoration explicit on normal and error paths while retaining a
  best-effort panic restoration guard.
- Use dependency injection around the interactive runtime for CLI and
  exit-code tests.

### TypeScript

- Keep Commander as the CLI parser.
- Use Ink and React for the inline startup component.
- Render with `exitOnCtrlC: false` so both supported exit keys follow the same
  explicit input path.
- Check `stdin.isTTY` and `stdout.isTTY` before calling Ink.
- Inject the interactive action into the Commander program for isolated CLI
  tests.
- Configure TypeScript for JSX and test the component independently from the
  real terminal.

### Python

- Keep Typer as the CLI parser.
- Use Textual in inline mode with no clear-on-exit behavior.
- Override Textual's default `Ctrl+C` behavior so both exit keys terminate
  immediately and successfully.
- Check `stdin.isatty()` and `stdout.isatty()` before constructing the Textual
  application.
- Keep the TUI application, terminal preflight, and Typer callback in separate
  modules.
- Add and lock every dependency through uv; do not add `requirements.txt`,
  pip, Poetry, Pipenv, or another project manager.

## Terminal Lifecycle

Framework-native lifecycle management is the primary restoration mechanism.
Implementations must not stack independent manual raw-mode or cursor control
on top of their framework unless a tested framework limitation requires it.

The required lifecycle properties are:

- no alternate-screen entry;
- no raw input mode left active after exit;
- cursor visibility restored after handled exits and errors;
- the two semantic startup lines remain visible after exit;
- no terminal mutation occurs on the non-TTY path.

The slice does not promise byte-identical ANSI sequences across frameworks.
Tests normalize terminal output and assert visible semantics plus terminal
state.

## Shared Contracts

Add an implementation-neutral lifecycle contract under `contracts/` that
defines:

- the four exact language labels;
- the exact exit hint;
- the exact non-TTY diagnostic;
- the exact internal-failure diagnostic;
- success, non-TTY, and internal-failure exit codes;
- `Ctrl+C` and `Ctrl+D` as the only exit inputs in this slice;
- the requirement that `--version` and `--help` bypass interactive startup.

The contract contains no ANSI sequences or framework-specific event names.
The existing contract validator must validate its shape and values.

## Testing Strategy

### Language Unit and Component Tests

Each implementation tests:

- `--version` and `--help` do not invoke the interactive runner;
- no arguments invoke the interactive runner exactly once;
- a non-TTY result maps to status `2` and the exact diagnostic;
- an internal failure maps to status `1`;
- the startup view contains the exact language banner and exit hint;
- `Ctrl+C` and `Ctrl+D` request successful exit;
- unrelated keys do not request exit.

Framework rendering tests assert normalized visible text rather than raw ANSI
bytes.

### Shared Non-TTY Black-Box Test

Run all four public root Make targets without a PTY and verify:

- status `2`;
- empty `stdout`;
- the exact shared diagnostic on `stderr`.

Run all four targets with `ARGS="--version"` in the same non-TTY environment
and retain the existing successful version checks.

### macOS PTY Lifecycle Test

A shared uv-executed Python harness uses the standard-library PTY and terminal
modules to launch each public Make target. For every language and for both
exit keys, it:

1. records the pseudo-terminal attributes;
2. starts the implementation;
3. waits for the language banner and exit hint;
4. sends the corresponding control byte;
5. requires process status `0`;
6. compares terminal attributes after exit;
7. normalizes captured output and confirms the startup view remains present.

This produces eight startup-and-exit scenarios. A bounded timeout terminates a
hung child and reports its captured output.

### CI

- Keep all existing language, version, run-target, contract, and artifact
  tests.
- Add the shared non-TTY test to the aggregate root test target.
- Run the PTY lifecycle test in the existing macOS job that already provisions
  all four language toolchains.
- Pull requests must exercise the lifecycle tests.
- Artifact builds continue to validate `--version` without a TTY.

## Documentation

Update the README to state that the current slice starts a minimal interactive
TUI and to show:

```sh
make run-go
make run-rust
make run-typescript
make run-python
```

Document that interactive mode needs a terminal, while `--version` and
`--help` remain suitable for scripts and CI.

## Explicitly Deferred

The following remain outside this slice:

- editable input and Unicode grapheme navigation;
- Backspace, Delete, Home, End, and submission behavior;
- user messages and assistant messages;
- deterministic simulated streaming;
- stable committed message history;
- response cancellation and failure recovery;
- terminal resize and active-region reflow;
- renderer snapshot parity and release preparation;
- LLM, network, file, shell, permission, agent-tool, plugin, or MCP behavior;
- Linux and Windows support.

## Acceptance Criteria

The slice is complete when:

- every no-argument root Make target opens the approved two-line inline startup
  view in a macOS terminal;
- all four implementations exit successfully through both `Ctrl+C` and
  `Ctrl+D`;
- all handled exits restore terminal state and preserve the startup view;
- all four non-TTY invocations emit the exact diagnostic and exit `2`;
- `--version` and `--help` remain non-interactive and successful;
- shared contracts, language tests, non-TTY tests, and eight PTY scenarios pass
  locally and in GitHub Actions;
- Python dependency management and test execution use uv exclusively;
- existing artifact and CI-policy behavior remains green.
