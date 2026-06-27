.PHONY: help install sync lock lint format format-fix typecheck test test-cov \
        quality spell toml-check workflow-audit workflow-syntax security-audit \
        sbom dead-code dependency-check clean

PYTHON ?= python
PKG := fyi_archive

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: sync ## Install dev environment with uv (editable)
	uv sync --extra dev

sync: ## Sync env from the lockfile (frozen)
	uv sync --extra dev --frozen

lock: ## Regenerate the lockfile
	uv lock

lint: ## Ruff lint
	uv run ruff check src tests scripts

format: ## Check formatting
	uv run ruff format --check src tests scripts

format-fix: ## Apply formatting + lint fixes
	uv run ruff check --fix src tests scripts
	uv run ruff format src tests scripts

typecheck: ## ty type check
	uv run ty check src

test: ## Run the test suite
	uv run pytest -q

test-cov: ## Run tests with coverage
	uv run pytest --cov=$(PKG) --cov-report=term-missing --cov-report=html

quality: lint format typecheck spell toml-check workflow-audit workflow-syntax ## Full quality gate

spell: ## typos spelling check
	uv run typos src tests scripts docs README.md

toml-check: ## taplo TOML check
	taplo check --config=.taplo.toml pyproject.toml || true

workflow-audit: ## zizmor GHA security audit
	zizmor --min-severity medium .github/workflows || true

workflow-syntax: ## actionlint workflow syntax
	actionlint || true

security-audit: ## pip-audit over the installed env
	uv run pip-audit || true

sbom: ## Generate CycloneDX SBOM
	uv run cyclonedx-py environment --output-format json --output-file dist/sbom.cdx.json

dead-code: ## vulture dead-code scan
	uv run vulture src || true

dependency-check: ## deptry dependency hygiene
	uv run deptry src || true

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .ty_cache .mypy_cache .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
