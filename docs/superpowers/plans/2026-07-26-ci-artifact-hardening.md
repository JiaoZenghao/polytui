# CI Artifact Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve executable permissions in Go and Rust downloads, run the new regression contracts in pull-request CI, and validate every artifact upload within its exact job and step.

**Architecture:** A shared shell builder creates architecture-qualified native `tar.gz` archives, while a black-box test extracts and executes each archive before CI uploads it. The artifact-policy validator scopes assertions first to a job and then to the named upload step, preventing unrelated global lines from satisfying the policy. Existing language jobs remain independent.

**Tech Stack:** POSIX shell, GNU Make, Go 1.26.5, Rust 1.97.1/Cargo, macOS `tar`, GitHub Actions, `actions/upload-artifact@v7`

## Global Constraints

- M1 remains macOS-only.
- Go and Rust downloads are `tar.gz` archives containing an executable named `polytui`.
- Archive filenames are `polytui-<language>-macos-<architecture>.tar.gz`.
- Extracted native commands must report `polytui 0.1.0-dev.0 (<language>)`.
- Python continues to use uv exclusively.
- TypeScript and Python artifact formats remain unchanged.
- Artifact upload runs only for pushes to `refs/heads/main`.
- Artifact retention remains exactly 30 days.
- Missing artifact files fail the workflow.
- Pull-request CI runs `scripts/validate-ci-artifacts.sh` and `scripts/test-run-targets.sh`.
- M1 artifacts remain unsigned and unnotarized; documentation must distinguish Gatekeeper approval from executable permission.
- Generated output remains under ignored `artifacts/`.

---

## File map

- `scripts/build-native-artifact.sh`: builds and packages one Go or Rust native artifact.
- `scripts/test-native-artifact-archive.sh`: extracts one generated archive, checks its mode, and executes its version command.
- `scripts/validate-ci-artifacts.sh`: validates exact job and upload-step policy.
- `.github/workflows/ci.yml`: calls the native archive checks and runs both regression scripts in PR CI.
- `README.md`: documents archive extraction and the unsigned Gatekeeper limitation.

### Task 1: Executable native archives

**Files:**
- Create: `scripts/build-native-artifact.sh`
- Create: `scripts/test-native-artifact-archive.sh`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `scripts/build-native-artifact.sh <go|rust> <architecture>`.
- Produces: `artifacts/<language>/polytui-<language>-macos-<architecture>.tar.gz`.
- Verifies: `scripts/test-native-artifact-archive.sh <go|rust> <architecture>`.

- [ ] **Step 1: Write the failing archive test**

Create `scripts/test-native-artifact-archive.sh`:

```sh
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
```

Make it executable:

```sh
chmod +x scripts/test-native-artifact-archive.sh
```

- [ ] **Step 2: Verify RED**

Run:

```sh
./scripts/test-native-artifact-archive.sh go TEST
```

Expected: FAIL because `scripts/build-native-artifact.sh` does not exist.

- [ ] **Step 3: Implement the native artifact builder**

Create `scripts/build-native-artifact.sh`:

```sh
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
```

Make it executable:

```sh
chmod +x scripts/build-native-artifact.sh
```

- [ ] **Step 4: Verify GREEN for both languages**

Run:

```sh
./scripts/test-native-artifact-archive.sh go TEST
./scripts/test-native-artifact-archive.sh rust TEST
```

Expected: both commands print `verified` followed by their exact archive path.

- [ ] **Step 5: Use verified tar archives in GitHub Actions**

Replace the Go build and upload path with:

```yaml
      - name: Build and verify Go artifact
        run: ./scripts/test-native-artifact-archive.sh go "${{ runner.arch }}"
      - name: Upload Go artifact
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v7
        with:
          name: polytui-go-macos-${{ runner.arch }}
          path: artifacts/go/polytui-go-macos-${{ runner.arch }}.tar.gz
          retention-days: 30
          if-no-files-found: error
```

Replace the Rust build and upload path with:

```yaml
      - name: Build and verify Rust artifact
        run: ./scripts/test-native-artifact-archive.sh rust "${{ runner.arch }}"
      - name: Upload Rust artifact
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        uses: actions/upload-artifact@v7
        with:
          name: polytui-rust-macos-${{ runner.arch }}
          path: artifacts/rust/polytui-rust-macos-${{ runner.arch }}.tar.gz
          retention-days: 30
          if-no-files-found: error
```

- [ ] **Step 6: Verify Task 1**

Run:

```sh
./scripts/test-native-artifact-archive.sh go TEST
./scripts/test-native-artifact-archive.sh rust TEST
git diff --check
```

Expected: both archives extract to executable commands, both version checks
pass, and Git reports no whitespace errors.

- [ ] **Step 7: Commit**

```sh
git add scripts/build-native-artifact.sh scripts/test-native-artifact-archive.sh .github/workflows/ci.yml
git commit -m "ci: preserve native artifact permissions"
```

### Task 2: Job-scoped policy validation and CI regression coverage

**Files:**
- Modify: `scripts/validate-ci-artifacts.sh`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: named jobs and named steps in `.github/workflows/ci.yml`.
- Produces: a failing policy test when an upload condition, path, command, or regression invocation is moved or changed.

- [ ] **Step 1: Replace global assertions with job- and step-scoped assertions**

Replace `scripts/validate-ci-artifacts.sh` with:

```sh
#!/bin/sh
set -eu

workflow=".github/workflows/ci.yml"

job_block() {
	job="$1"
	awk -v target="$job" '
		$0 == "  " target ":" { inside = 1 }
		inside && $0 ~ /^  [[:alnum:]_-]+:$/ && $0 != "  " target ":" { exit }
		inside { print }
	' "$workflow"
}

step_block() {
	job="$1"
	step="$2"
	job_block "$job" | awk -v target="$step" '
		$0 == "      - name: " target { inside = 1 }
		inside && $0 ~ /^      - / && $0 != "      - name: " target { exit }
		inside { print }
	'
}

assert_exact_line() {
	scope="$1"
	content="$2"
	line="$3"
	expected="${4:-1}"
	actual="$(printf '%s\n' "$content" | grep -Fxc -- "$line" || true)"

	if [ "$actual" -ne "$expected" ]; then
		printf '%s: expected %s exact line(s) "%s", found %s\n' \
			"$scope" "$expected" "$line" "$actual" >&2
		exit 1
	fi
}

assert_job_line() {
	job="$1"
	line="$2"
	assert_exact_line "$job" "$(job_block "$job")" "$line"
}

assert_step_line() {
	job="$1"
	step="$2"
	line="$3"
	block="$(step_block "$job" "$step")"

	if [ -z "$block" ]; then
		printf '%s / %s: missing step\n' "$job" "$step" >&2
		exit 1
	fi

	assert_exact_line "$job / $step" "$block" "$line"
}

assert_upload() {
	job="$1"
	step="$2"
	name="$3"
	path="$4"
	assert_step_line "$job" "$step" "        if: github.event_name == 'push' && github.ref == 'refs/heads/main'"
	assert_step_line "$job" "$step" "        uses: actions/upload-artifact@v7"
	assert_step_line "$job" "$step" "          name: $name"
	assert_step_line "$job" "$step" "          path: $path"
	assert_step_line "$job" "$step" "          retention-days: 30"
	assert_step_line "$job" "$step" "          if-no-files-found: error"
}

assert_job_line validate-contracts "      - run: ./scripts/validate-contracts.sh"
assert_job_line validate-contracts "      - run: ./scripts/validate-ci-artifacts.sh"
assert_job_line blackbox-parity-macos "      - run: ./scripts/check-versions.sh"
assert_job_line blackbox-parity-macos "      - run: ./scripts/test-run-targets.sh"

assert_step_line test-go-macos "Build and verify Go artifact" \
	'        run: ./scripts/test-native-artifact-archive.sh go "${{ runner.arch }}"'
assert_upload test-go-macos "Upload Go artifact" \
	'polytui-go-macos-${{ runner.arch }}' \
	'artifacts/go/polytui-go-macos-${{ runner.arch }}.tar.gz'

assert_step_line test-rust-macos "Build and verify Rust artifact" \
	'        run: ./scripts/test-native-artifact-archive.sh rust "${{ runner.arch }}"'
assert_upload test-rust-macos "Upload Rust artifact" \
	'polytui-rust-macos-${{ runner.arch }}' \
	'artifacts/rust/polytui-rust-macos-${{ runner.arch }}.tar.gz'

assert_step_line test-typescript-macos "Build TypeScript artifact" \
	"        run: pnpm run build"
assert_step_line test-typescript-macos "Stage TypeScript artifact" \
	"          cp -R dist ../../artifacts/typescript/dist"
assert_step_line test-typescript-macos "Stage TypeScript artifact" \
	"          cp package.json ../../artifacts/typescript/package.json"
assert_upload test-typescript-macos "Upload TypeScript artifact" \
	"polytui-typescript" "artifacts/typescript"

assert_step_line test-python-macos-uv "Build Python artifact" \
	"        run: uv build --out-dir ../../artifacts/python"
assert_upload test-python-macos-uv "Upload Python artifact" \
	"polytui-python" "artifacts/python"

printf '%s\n' "GitHub Actions artifact policy is valid"
```

- [ ] **Step 2: Verify RED**

Run:

```sh
./scripts/validate-ci-artifacts.sh
```

Expected: FAIL because `validate-contracts` does not yet run
`./scripts/validate-ci-artifacts.sh`.

- [ ] **Step 3: Wire both regression tests into CI**

After contract validation in `validate-contracts`, add:

```yaml
      - run: ./scripts/validate-ci-artifacts.sh
```

After version parity in `blackbox-parity-macos`, add:

```yaml
      - run: ./scripts/test-run-targets.sh
```

- [ ] **Step 4: Verify GREEN and mutation sensitivity**

Run:

```sh
./scripts/validate-ci-artifacts.sh
```

Expected: PASS with `GitHub Actions artifact policy is valid`.

Then temporarily change the Go upload path in `.github/workflows/ci.yml` to
`artifacts/go/wrong.tar.gz`, run the validator, and confirm it fails with the
missing exact Go path. Restore the correct path with `apply_patch`, rerun the
validator, and confirm it passes.

- [ ] **Step 5: Run the aggregate suite**

Run:

```sh
make test
git diff --check
```

Expected: all language, version, run-target, contract, and CI policy checks
pass with no whitespace errors.

- [ ] **Step 6: Commit**

```sh
git add scripts/validate-ci-artifacts.sh .github/workflows/ci.yml
git commit -m "test: enforce artifact policy in CI"
```

### Task 3: Download documentation and final verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the Go and Rust `tar.gz` artifact layout.
- Produces: exact extraction, execution, and Gatekeeper guidance.

- [ ] **Step 1: Document native archive extraction**

Under `Download CI artifacts`, explain that downloading a GitHub artifact
produces a ZIP containing the native `tar.gz`. Add:

````markdown
For Go or Rust, unzip the GitHub artifact and then extract its native archive:

```sh
tar -xzf polytui-go-macos-ARM64.tar.gz
./polytui --version
```

The inner `tar.gz` preserves the executable permission of `polytui`.
````

- [ ] **Step 2: Document the Gatekeeper boundary**

Add:

```markdown
M1 artifacts are not signed with an Apple Developer ID and are not notarized.
If macOS blocks a build that you produced or downloaded from this trusted
repository, open **System Settings > Privacy & Security** and choose
**Open Anyway** for `polytui`. Executable permission and Apple notarization are
separate concerns.
```

- [ ] **Step 3: Run final local verification**

Run:

```sh
./scripts/test-native-artifact-archive.sh go TEST
./scripts/test-native-artifact-archive.sh rust TEST
make test
git diff --check
git status --short
```

Expected: both archives preserve executable commands and version output, the
full suite exits 0, no whitespace errors exist, and only `README.md` is
uncommitted before the documentation commit.

- [ ] **Step 4: Commit**

```sh
git add README.md
git commit -m "docs: explain native artifact downloads"
```

- [ ] **Step 5: Review the completed branch**

Run:

```sh
git log --oneline main..HEAD
git diff --stat main...HEAD
make test
```

Expected: two approved design commits, this implementation plan commit, and
three focused implementation commits; the final suite exits 0.

## Live GitHub acceptance

After pushing the branch:

1. Confirm pull-request CI runs `validate-ci-artifacts.sh` and
   `test-run-targets.sh`.
2. Confirm all four language jobs build successfully while upload steps are
   skipped on the pull request.
3. Merge only after all checks pass.
4. Confirm the `main` workflow publishes four artifacts.
5. Download the Go and Rust artifacts, extract both archive layers, confirm
   `polytui` is executable, and run `--version`.
