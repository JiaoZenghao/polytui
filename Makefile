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
