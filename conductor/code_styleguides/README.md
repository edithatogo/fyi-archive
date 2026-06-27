# Code Styleguide

Enforced by `ruff` (see `pyproject.toml`). Highlights:

- **Formatting:** `ruff format` — double quotes, 4-space indent, LF line endings,
  magic-trailing-comma respected. Line length 100.
- **Imports:** sorted by ruff (`I`). No star imports.
- **Types:** strict annotations everywhere except `tests/*` and `scripts/*`. Checked
  by `ty`.
- **Docstrings:** modules, public classes, and public functions carry docstrings
  (Google-style). Tests relax docstring rules.
- **Error handling:** specific exceptions; no bare `except` (`S110` ignored only where
  documented).
- **Logging:** `loguru`; no `print` outside `scripts/*`/`tests/*` (`T20`).
- **Commits:** Conventional Commits — consumed by `release-please`.

## Markdown & prose

- `markdownlint-cli` (config in `.markdownlint.json`): line length 160, fenced
  backtick code blocks, asterisk emphasis.
- `vale` (config in `.vale.ini`): `MinAlertLevel = suggestion`.
