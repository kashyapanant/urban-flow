.PHONY: install install-dev run lint format format-check test test-cov clean

# Use uv for running commands (respects venv from uv sync)
UV := uv run

install:
	uv sync

install-dev:
	uv sync --group dev

run:
	$(UV) python main.py

lint:
	$(UV) ruff check .
	$(UV) ruff format --check .

format:
	$(UV) ruff check --fix .
	$(UV) ruff format .

test:
	$(UV) pytest

test-cov:
	$(UV) pytest --cov --cov-report=term-missing

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
