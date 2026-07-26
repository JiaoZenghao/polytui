# Four-Language CLI/TUI Monorepo Design

Date: 2026-07-26

## Purpose

Build the same terminal application independently in Go, Rust, TypeScript, and Python so the repository can be used to learn and compare modern CLI/TUI development.

The long-term product direction is similar to Codex CLI, but the first milestone deliberately covers only terminal interaction fundamentals. It does not connect to a model or execute tools.

## Confirmed Decisions

- Use one GitHub monorepo.
- Name the project and all four executable entry points `polytui`.
- Keep one independent folder for each language.
- Develop all four implementations through synchronized vertical milestones.
- Treat the shared behavior contract as the source of truth.
- Allow each language to use idiomatic internal architecture.
- Initially support macOS only.
- Use a Codex-style inline interface rather than the alternate full-screen buffer.
- Use deterministic simulated streaming in the first milestone.
- Manage Python exclusively with `uv`.
- Use one synchronized SemVer version for the entire monorepo.

## Scope

### Milestone M1

M1 establishes a behaviorally equivalent inline TUI in all four languages:

- language-specific startup banner;
- single-line Unicode input;
- cursor movement with Left, Right, Home, and End;
- editing with Backspace and Delete;
- submission with Enter;
- deterministic simulated streaming;
- visible streaming, completed, and cancelled states;
- cancellation and exit key handling;
- reflow of the active area when terminal width changes;
- completed content retained in terminal scrollback;
- clear errors and reliable terminal restoration.

### Not in M1

- real LLM or network integration;
- Markdown, syntax highlighting, or diff rendering;
- multiline editing or input history;
- session persistence;
- file, shell, permission, or other agent tools;
- mouse interaction or theme configuration;
- Linux or Windows support;
- plugins or MCP.

These items require later, separately approved milestone designs.

## Repository Structure

```text
cli_tui/
├── README.md
├── CHANGELOG.md
├── VERSION
├── docs/
│   ├── architecture/
│   ├── comparisons/
│   └── superpowers/specs/
├── contracts/
│   ├── events/
│   ├── scenarios/
│   ├── snapshots/
│   └── schema/
├── implementations/
│   ├── go/
│   ├── rust/
│   ├── typescript/
│   └── python/
├── scripts/
└── .github/workflows/
```

Each implementation owns its dependencies, source code, tests, build output, and language-specific documentation. Implementations must not import source code from one another.

The local workspace directory may remain `cli_tui`, but the GitHub repository, release name, package identity, and user-facing command are `polytui`.

The `contracts/` directory describes observable behavior, not internal classes, modules, concurrency primitives, or framework APIs.

## Common Architecture

All four implementations follow the same conceptual boundaries:

1. **CLI** parses arguments and starts the interactive application.
2. **Terminal adapter** converts framework-specific keys, size changes, and signals into domain events.
3. **Domain update** applies one event to the current application state and returns the next state plus descriptions of required effects.
4. **Stream adapter** turns a shared scenario into deterministic stream events.
5. **Renderer** converts application state into stable history and the currently active inline region.

The data flow is one-way:

```text
terminal input
  → domain event
  → state update
  → effect description
  → framework adapter
  → next event

state
  → renderer
  → stable history + active inline region
```

State updates do not directly read the terminal, write output, sleep, or call the network. This makes the same behavior independently testable in every language.

## Common State and Events

The observable state includes:

- current input text;
- cursor position;
- committed messages;
- streaming status;
- active stream buffer;
- terminal width;
- exit request state;
- optional user-facing error.

The common event vocabulary includes:

- key pressed;
- input submitted;
- stream started;
- stream chunk received;
- stream completed;
- stream cancelled;
- stream failed;
- terminal resized;
- exit requested.

Languages may represent these concepts with structs, enums, discriminated unions, classes, messages, or framework-native types.

## Interaction Rules

- Enter submits non-empty input and starts the configured simulated response.
- Enter on empty input has no effect.
- Cursor movement and deletion operate on Unicode grapheme clusters, not bytes or code points.
- Layout width is measured in terminal display cells so wide and combining characters behave consistently.
- While streaming, Ctrl+C cancels the response, retains received content, and marks it cancelled.
- While idle with non-empty input, Ctrl+C clears the input.
- While idle with empty input, Ctrl+C exits successfully.
- Ctrl+D exits successfully only when the input is empty.
- Completed messages are committed to terminal scrollback and are not continually redrawn.
- Resize events reflow only the active region; previously committed terminal output remains untouched.
- M1 allows only one in-flight response. Input is unavailable until the response completes or is cancelled.

## Language Stacks

### Go

- Go Modules for project and dependency management
- Bubble Tea for the event loop and inline TUI
- Lip Gloss for terminal styling and width-aware presentation
- Cobra for CLI parsing and future subcommands
- Go's standard test tooling, supplemented only where terminal integration requires it

### Rust

- Cargo for project, dependency, build, and test management
- Ratatui with an inline viewport for buffered rendering
- Crossterm for terminal input and control
- Clap for CLI parsing and future subcommands
- Cargo test, with focused rendering helpers where required

### TypeScript

- pnpm for project and dependency management
- Ink and React for declarative terminal components
- Commander for CLI parsing and future subcommands
- Vitest and Ink testing utilities for state and component tests

### Python

- `uv` as the exclusive project manager
- `pyproject.toml` for project metadata and dependencies
- committed `uv.lock` for reproducible dependency resolution
- uv-managed virtual environment, run commands, and test commands
- Textual in inline mode for the TUI
- Typer for CLI parsing and future subcommands
- pytest and Textual Pilot for state and interaction tests

The Python implementation does not maintain `requirements.txt`, Pipenv, or Poetry configuration.

## Shared Contracts

Shared contracts use portable, implementation-neutral data:

- JSON Schema defines contract file structure.
- JSON event sequences describe deterministic state transitions.
- JSON scenarios provide simulated response chunks and error cases.
- UTF-8 text snapshots describe normalized visible output at fixed terminal widths.

Contracts never contain ANSI escape sequences as their expected semantic output. Framework-specific rendering tests may test ANSI behavior inside their own implementation.

Each contract declares a stable identifier and contract format version so later schema evolution is explicit.

## Error Handling and Terminal Safety

- Starting interactive mode without a TTY produces a concise diagnostic on stderr and a shared non-zero exit code.
- A non-TTY invocation exits with code 2; an unexpected internal failure exits with code 1.
- Normal exit, Ctrl+C, and handled errors restore cursor visibility and terminal input mode.
- Each implementation installs a top-level restoration guard appropriate to its language and framework.
- Shared simulated failure scenarios display a user-facing error and return to an editable state.
- Normal interface output goes to stdout; diagnostics go to stderr.
- Stack traces are not shown by default.
- Unexpected internal failures exit non-zero after attempting terminal restoration.

## Testing Strategy

### Layer 1: Domain Unit Tests

Inject shared events into pure state transitions and assert next state and requested effects. This is the largest and fastest test layer.

### Layer 2: Renderer Tests

Render fixed states at fixed terminal widths and compare normalized text frames. ANSI sequences and framework-private metadata are removed before cross-language comparison.

### Layer 3: macOS PTY Smoke Tests

Start each executable in a pseudo-terminal and test a small number of critical paths:

- start and display the language banner;
- submit text;
- receive deterministic chunks;
- cancel an active response;
- resize the terminal;
- exit through Ctrl+C and Ctrl+D;
- verify that the terminal is restored.

The black-box layer verifies behavior, not byte-for-byte ANSI identity.

## GitHub and CI

The protected `main` branch represents a state where all four implementations satisfy the current shared contract.

Required macOS checks are:

- `validate-contracts`;
- `test-go-macos`;
- `test-rust-macos`;
- `test-typescript-macos`;
- `test-python-macos-uv`;
- `blackbox-parity-macos`.

Development uses short-lived branches and one pull request per vertical feature. A feature PR includes the contract change and all four implementations. Commits inside the PR are split into reviewable scopes such as `contracts`, `go`, `rust`, `typescript`, and `python`.

GitHub Issues use milestone and language labels. A vertical feature remains incomplete until all four language tasks and the shared parity check pass.

## Versioning

- The monorepo has one SemVer version line.
- The root `VERSION` file is the version source of truth; CI verifies every implementation reports it.
- All four implementations report the same version.
- A root `CHANGELOG.md` records user-visible behavior changes.
- Git tags and GitHub Releases apply to the entire repository.
- Completing M1 produces the first planned release, `v0.1.0`.
- Individual language implementations are not independently versioned during M1.

## Planned M1 Vertical Slices

1. Repository skeleton, contract validation, and four buildable CLI entry points.
2. Startup, TTY validation, terminal lifecycle, and clean exit.
3. Shared state model and single-line input editing.
4. Deterministic simulated streaming and stable history.
5. Cancellation, failure scenarios, and resize behavior.
6. Renderer normalization, PTY parity tests, CI gates, and `v0.1.0` release preparation.

Each slice is complete only when its shared contract and all four implementations pass.

## M1 Completion Criteria

M1 is complete when:

- all required user-visible behaviors are implemented in all four languages;
- all six macOS GitHub checks pass;
- Python setup, run, and test workflows use uv;
- a new contributor can run every implementation from documented root commands;
- the four programs pass the same PTY scenarios;
- terminal state is restored after normal exit, cancellation, and handled failures;
- the repository is ready to tag `v0.1.0`.
