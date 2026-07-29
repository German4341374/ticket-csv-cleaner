.PHONY: setup format lint typecheck test coverage build demo docker-build clean

setup:
	uv sync --frozen --extra dev

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest -q

coverage:
	uv run pytest -q --cov=ticket_csv_cleaner --cov-report=term-missing --cov-report=html

build:
	uv build --no-sources

demo:
	uv run ticket-csv-cleaner clean examples/tickets.csv --config examples/rules.yaml --output-dir output

docker-build:
	docker build --tag ticket-csv-cleaner:local .

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache build dist htmlcov output
