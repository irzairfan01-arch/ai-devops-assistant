# AI DevOps Assistant

![CI Status](https://img.shields.io/badge/build-passing-brightgreen)
![Version](https://img.shields.io/pypi/v/ai-devops-assistant)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

An air-gapped, open-source AI DevOps Assistant pipeline using GitPython, Ruff, pytest, Bandit, Semgrep, Ollama, Docker, and MCP.
This tool automates static analysis, tests, AI code review, STRIDE threat modeling, and container validation, completely locally.

## Features

- 🔌 **Comprehensive Scanners:** Ruff, Bandit, Semgrep, Mypy, Pylint, Safety, and Trivy.
- 🧠 **AI Code Review:** Automated PR-style code review using local LLMs via Ollama.
- 🛡️ **STRIDE Threat Modeling:** AI-powered security threat generation based on detected violations and code diffs.
- 🪄 **Auto-fix Engine:** Generates code fixes for detected violations and safely applies them.
- 🧪 **Test Generation:** Generates comprehensive `pytest` test files for your code.
- 🌐 **Live Web Dashboard:** Real-time pipeline streaming, historical trends, and detailed HTML reports.
- 🔁 **CI/CD Integrations:** Generate ready-to-use GitHub Actions, GitLab CI, or Git pre-commit hooks.
- 🐳 **Docker Validation:** Automatically verifies that your `Dockerfile` builds successfully.

## Installation

You can install the tool directly from PyPI (or locally):

```bash
pip install ai-devops-assistant
```

To include all optional dependencies (like the web dashboard and extra scanners):

```bash
pip install "ai-devops-assistant[all]"
```

## Quick Start

### 1. Start Ollama

Ensure Ollama is installed and running with your preferred model (default: `qwen2.5-coder`):

```bash
ollama serve &
ollama pull qwen2.5-coder
```

### 2. Run the Pipeline

Run the full CI/CD audit on a local directory:

```bash
devops-assistant run --path /path/to/your/repo
```

### 3. Launch the Web Dashboard

View historical runs, trend graphs, and live reports:

```bash
devops-assistant web --port 8080
```
Then open `http://localhost:8080` in your browser.

## CLI Usage

```bash
# Run the pipeline with auto-fix enabled
devops-assistant run --path . --auto-fix

# Generate AI tests for your modules
devops-assistant run --path . --write-tests

# Generate a GitHub Actions workflow for this tool
devops-assistant generate-ci github

# Run just the static linters
devops-assistant lint .
```

## Configuration

You can configure thresholds and alert behavior in your `pyproject.toml`:

```toml
[tool.devops-assistant.alerts]
min_quality_score = 75
max_violations = 10
slack_webhook = "https://hooks.slack.com/services/..."
```

## License

This project is licensed under the MIT License.
