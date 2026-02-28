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
	# This command checks if all Python files are formatted according to Ruff's style rules and Black's formatting rules, without making changes.
	$(UV) ruff format --check .
	# This command formats all Python files according to Ruff's style rules and Black's formatting rules.

format:
	# This command checks if all Python files are formatted according to Ruff's style rules and Black's formatting rules, and makes changes to the files to fix any issues.
	$(UV) ruff check --fix .
	# This command formats all Python files according to Ruff's style rules and Black's formatting rules.
	$(UV) black .

test:
	$(UV) pytest

test-cov:
	$(UV) pytest --cov --cov-report=term-missing

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
