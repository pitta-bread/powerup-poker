.DEFAULT_GOAL := check

.PHONY: check test lint

check: test lint

test:
	uv run python -m unittest -v tests

lint:
	uv run ruff check .
