.PHONY: contracts test-go test-rust test-typescript test-python versions test ci-artifacts-policy run-go run-rust run-typescript run-python test-run-targets

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

ci-artifacts-policy:
	./scripts/validate-ci-artifacts.sh

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

test: contracts test-go test-rust test-typescript test-python versions ci-artifacts-policy test-run-targets
