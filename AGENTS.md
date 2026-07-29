# Repository guidance

- Keep source, tests, fixtures, configuration, documentation, and commits in English.
- Never add real tickets, personal data, credentials, tokens, or private exports.
- Preserve strict mypy and Ruff checks.
- Keep processing deterministic and avoid global mutable state.
- Keep `clean.csv`, `rejected.csv`, and `warnings.csv` mutually exclusive.
- Add tests for every validation or normalization rule.
- Run `make lint`, `make typecheck`, `make test`, and `make build`.
- Use Conventional Commits.
