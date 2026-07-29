# Contributing

Keep changes focused on safe, deterministic preprocessing of Service Desk CSV exports.

## Development workflow

1. Install [uv](https://docs.astral.sh/uv/).
2. Run `uv sync --frozen --extra dev`.
3. Add or update invented fixtures and tests.
4. Run `make lint`, `make typecheck`, `make test`, and `make build`.
5. Build the container when Docker is available.
6. Open a pull request using the repository template.

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add a priority alias`
- `fix: reject extra CSV values`
- `test: cover UTF-16 detection`
- `docs: clarify dry-run behavior`

Never submit real tickets, names, email addresses, phone numbers, access tokens, credentials, or proprietary CSV exports.
