# Local Run Commands and CI Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four root-level local CLI run commands and publish each language's native build output as a 30-day GitHub Actions artifact after successful pushes to `main`.

**Architecture:** Keep the four language projects independent and expose them through thin root `Makefile` targets. Extend the existing language-specific macOS CI jobs so each job tests, builds, stages, and conditionally uploads only its own native output. Use shell contract tests to validate the Make interface and workflow policy without coupling one language implementation to another.

**Tech Stack:** GNU Make, POSIX shell, Go 1.26.5, Rust 1.97.1/Cargo, Node.js 24.15.0/pnpm 10.33.2/TypeScript, Python 3.13.14/uv 0.8.9, GitHub Actions, `actions/upload-artifact@v7`

## Global Constraints

- M1 remains macOS-only.
- Local targets are exactly `run-go`, `run-rust`, `run-typescript`, and `run-python`.
- Every local target accepts optional arguments through `ARGS`.
- Python continues to use uv exclusively.
- Go and Rust artifacts are macOS executables named `polytui`.
- TypeScript publishes compiled `dist/` plus `package.json`.
- Python publishes both wheel and source distribution from `uv build`.
- Artifact upload runs only for pushes to `refs/heads/main`.
- Artifact retention is exactly 30 days.
- Missing artifact files fail the workflow.
- The workflow does not create GitHub Releases or publish GitHub Packages.
- Generated output is staged under `artifacts/` and is not committed.

---

## File map

- `Makefile`: public root commands and aggregate verification entry point.
- `scripts/test-run-targets.sh`: black-box contract for the four Make run targets.
- `scripts/validate-ci-artifacts.sh`: static policy checks for build and artifact upload configuration.
- `.github/workflows/ci.yml`: language-native builds and conditional artifact uploads.
- `.gitignore`: excludes the shared local artifact staging directory.
- `README.md`: documents local execution and artifact download behavior.

### Task 1: Root local-run contract

**Files:**
- Create: `scripts/test-run-targets.sh`
- Modify: `Makefile`

**Interfaces:**
- Consumes: the existing `VERSION` file and four existing CLI entry points.
- Produces: `make run-{go,rust,typescript,python} ARGS="<arguments>"`.

- [ ] **Step 1: Write the failing black-box test**

Create `scripts/test-run-targets.sh`:

```sh
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

check_target run-go go
check_target run-rust rust
check_target run-typescript typescript
check_target run-python python

printf '%s\n' "all local run targets report language-specific versions based on $version"
```

Make it executable:

```sh
chmod +x scripts/test-run-targets.sh
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```sh
./scripts/test-run-targets.sh
```

Expected: FAIL at `run-go` with `No rule to make target 'run-go'`.

- [ ] **Step 3: Add the minimal Make targets**

Extend `.PHONY` and add:

```make
.PHONY: run-go run-rust run-typescript run-python test-run-targets

run-go:
	@cd implementations/go && go run ./cmd/polytui $(ARGS)

run-rust:
	@cargo run --quiet --manifest-path implementations/rust/Cargo.toml -- $(ARGS)

run-typescript:
	@pnpm --dir implementations/typescript exec tsx src/index.ts $(ARGS)

run-python:
	@uv run --project implementations/python polytui $(ARGS)

test-run-targets:
	./scripts/test-run-targets.sh
```

Add `test-run-targets` to the dependencies of the existing aggregate `test`
target.

- [ ] **Step 4: Verify GREEN**

Run:

```sh
./scripts/test-run-targets.sh
make test
```

Expected: the black-box test prints
`all local run targets report language-specific versions based on 0.1.0-dev.0`,
and the full suite exits 0. Each target preserves the established full version
contract: `polytui 0.1.0-dev.0 (<language>)`.

- [ ] **Step 5: Commit the local-run contract**

```sh
git add Makefile scripts/test-run-targets.sh
git commit -m "feat: add local CLI run targets"
```

### Task 2: macOS native build artifacts

**Files:**
- Create: `scripts/validate-ci-artifacts.sh`
- Modify: `.github/workflows/ci.yml`
- Modify: `.gitignore`
- Modify: `Makefile`

**Interfaces:**
- Consumes: the language tests and build entry points already present in each CI job.
- Produces: four GitHub Actions artifacts named for Go, Rust, TypeScript, and Python.

- [ ] **Step 1: Write the failing workflow policy test**

Create `scripts/validate-ci-artifacts.sh`:

```sh
#!/bin/sh
set -eu

workflow=".github/workflows/ci.yml"

assert_count() {
	needle="$1"
	expected="$2"
	actual="$(grep -F -c -- "$needle" "$workflow" || true)"

	if [ "$actual" -ne "$expected" ]; then
		printf 'expected %s occurrences of "%s", found %s\n' \
			"$expected" "$needle" "$actual" >&2
		exit 1
	fi
}

assert_present() {
	needle="$1"
	if ! grep -F -q -- "$needle" "$workflow"; then
		printf 'missing workflow policy: %s\n' "$needle" >&2
		exit 1
	fi
}

assert_count "uses: actions/upload-artifact@v7" 4
assert_count "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" 4
assert_count "retention-days: 30" 4
assert_count "if-no-files-found: error" 4

assert_present "name: Build Go artifact"
assert_present "name: Build Rust artifact"
assert_present "name: Build TypeScript artifact"
assert_present "name: Build Python artifact"
assert_present "name: polytui-go-macos-\${{ runner.arch }}"
assert_present "name: polytui-rust-macos-\${{ runner.arch }}"
assert_present "name: polytui-typescript"
assert_present "name: polytui-python"

printf '%s\n' "GitHub Actions artifact policy is valid"
```

Make it executable:

```sh
chmod +x scripts/validate-ci-artifacts.sh
```

- [ ] **Step 2: Run the policy test and verify RED**

Run:

```sh
./scripts/validate-ci-artifacts.sh
```

Expected: FAIL with
`expected 4 occurrences of "uses: actions/upload-artifact@v7", found 0`.

- [ ] **Step 3: Ignore staged artifacts and register the policy check**

Append this generated-output rule to `.gitignore`:

```gitignore
/artifacts/
```

Add the following Make target and include it in `.PHONY` and aggregate `test`:

```make
ci-artifacts-policy:
	./scripts/validate-ci-artifacts.sh
```

- [ ] **Step 4: Build and upload the Go artifact**

After `go test ./...` in `test-go-macos`, add:

```yaml
      - name: Build Go artifact
        run: |
          mkdir -p ../../artifacts/go
          go build -trimpath -o ../../artifacts/go/polytui ./cmd/polytui
        working-directory: implementations/go
      - name: Upload Go artifact
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v7
        with:
          name: polytui-go-macos-${{ runner.arch }}
          path: artifacts/go/polytui
          retention-days: 30
          if-no-files-found: error
```

- [ ] **Step 5: Build and upload the Rust artifact**

After `cargo test --locked` in `test-rust-macos`, add:

```yaml
      - name: Build Rust artifact
        run: |
          cargo build --release --locked
          mkdir -p ../../artifacts/rust
          cp target/release/polytui ../../artifacts/rust/polytui
        working-directory: implementations/rust
      - name: Upload Rust artifact
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v7
        with:
          name: polytui-rust-macos-${{ runner.arch }}
          path: artifacts/rust/polytui
          retention-days: 30
          if-no-files-found: error
```

- [ ] **Step 6: Build and upload the TypeScript artifact**

Keep the existing `pnpm run build` step and name it `Build TypeScript
artifact`. Immediately after it, add:

```yaml
      - name: Stage TypeScript artifact
        run: |
          mkdir -p ../../artifacts/typescript
          cp -R dist ../../artifacts/typescript/dist
          cp package.json ../../artifacts/typescript/package.json
        working-directory: implementations/typescript
      - name: Upload TypeScript artifact
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v7
        with:
          name: polytui-typescript
          path: artifacts/typescript
          retention-days: 30
          if-no-files-found: error
```

The renamed build step must be:

```yaml
      - name: Build TypeScript artifact
        run: pnpm run build
        working-directory: implementations/typescript
```

- [ ] **Step 7: Build and upload the Python artifact**

After `uv run pytest -q` in `test-python-macos-uv`, add:

```yaml
      - name: Build Python artifact
        run: uv build --out-dir ../../artifacts/python
        working-directory: implementations/python
      - name: Upload Python artifact
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v7
        with:
          name: polytui-python
          path: artifacts/python
          retention-days: 30
          if-no-files-found: error
```

- [ ] **Step 8: Verify the workflow policy is GREEN**

Run:

```sh
./scripts/validate-ci-artifacts.sh
make test
git diff --check
```

Expected: policy validation prints
`GitHub Actions artifact policy is valid`; all language checks pass; Git
reports no whitespace errors.

- [ ] **Step 9: Commit CI artifact production**

```sh
git add .github/workflows/ci.yml .gitignore Makefile scripts/validate-ci-artifacts.sh
git commit -m "ci: publish native macOS artifacts"
```

### Task 3: User documentation and final verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the Make targets and artifact names implemented in Tasks 1 and 2.
- Produces: user-facing local run and artifact download instructions.

- [ ] **Step 1: Update the local-run documentation**

Replace the existing long-form commands under `Run each implementation` with:

````markdown
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
````

- [ ] **Step 2: Document workflow artifacts**

Add:

```markdown
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
```

- [ ] **Step 3: Run complete local verification**

Run:

```sh
make test
git diff --check
git status --short
```

Expected:

- contract validation succeeds;
- Go, Rust, TypeScript, and Python tests pass;
- all four local run targets preserve the full version text
  `polytui 0.1.0-dev.0 (<language>)`;
- artifact policy validation succeeds;
- only the intended README change remains uncommitted before the final commit;
- local `.pnpm-store/` and `AGENTS.md` remain untracked and are not staged.

- [ ] **Step 4: Commit documentation**

```sh
git add README.md
git commit -m "docs: explain local runs and CI artifacts"
```

- [ ] **Step 5: Review the completed branch**

Run:

```sh
git log --oneline main..HEAD
git diff --stat main...HEAD
make test
```

Expected: one design commit plus three implementation commits, a focused diff
covering the files in this plan, and a final test exit code of 0.

## Live GitHub acceptance

After the implementation branch is pushed and reviewed:

1. Confirm the pull request CI builds all four native outputs without artifact
   upload steps running.
2. Merge the pull request into `main`.
3. Confirm the resulting `main` workflow exposes four downloadable artifacts.
4. Inspect the artifact names and contents and confirm their expiration is 30
   days after creation.
