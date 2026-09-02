# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-02

### Added
- **More Scanners**: Added `mypy`, `pylint`, `safety`, and `trivy` integrations.
- **Web Dashboard**: Added a Flask-based live web dashboard (`devops-assistant web`) for viewing historical runs, trend graphs, and live SSE streaming of the pipeline.
- **Auto-Fix Engine**: AI can now generate and safely apply code fixes directly to the repository (with automatic git commit creation).
- **Test Generation**: Generates comprehensive `pytest` test files for source modules using Ollama.
- **Threat Modeling**: Generates structured STRIDE threat models from security violations and git diffs.
- **Metrics & Alerts**: Quality score and violation metrics are tracked over time. Added configurable Slack and Email alerts for regressions.
- **CI/CD Generator**: Added `devops-assistant generate-ci` command to generate GitHub Actions, GitLab CI, and Git pre-commit hooks.
- **Package Distribution**: Added PyPI publishing workflow and proper metadata to `pyproject.toml`.

### Changed
- The HTML Report was updated to a compact UI that fits on a single screenshot.
- Increased Ollama timeout to 300 seconds to handle initial model loading times.

## [1.0.0] - 2026-09-01

### Added
- Initial release of AI DevOps Assistant.
- Git ingestion, static analysis (Ruff, Bandit, Semgrep), pytest execution, AI code review, and Docker validation.
- Markdown and HTML report generation.
- MCP Server interface.
