"""
Main CLI Application Entrypoint for AI DevOps Assistant.
"""

import os
import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Force UTF-8 encoding for Windows standard output streams
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from devops_assistant.config import PipelineConfig, CIReportData, AlertConfig
from devops_assistant.git_manager import GitManager
from devops_assistant.scanners import (
    run_ruff, run_bandit, run_semgrep,
    run_mypy, run_pylint, run_safety, run_trivy,
)
from devops_assistant.test_engine import run_pytest, generate_tests_for_repo
from devops_assistant.ai_review import run_ai_code_review
from devops_assistant.ai_review.threat_model import run_threat_model
from devops_assistant.ai_review.autofix import run_autofix
from devops_assistant.docker_engine import validate_docker_build
from devops_assistant.reporter import generate_markdown_report, generate_html_report
from devops_assistant.mcp_server import start_mcp_server
from devops_assistant.metrics import check_and_alert
from devops_assistant.cicd import generate_github_actions, generate_gitlab_ci, generate_pre_commit_hook

app = typer.Typer(
    name="devops-assistant",
    help="AI DevOps Assistant pipeline.",
    add_completion=False
)
console = Console(force_terminal=True)


@app.command("run")
def run_pipeline(
    repo: str = typer.Option(None, "--repo", "-r", help="Git repository URL to clone"),
    path: str = typer.Option(".", "--path", "-p", help="Target repository directory path"),
    branch: str = typer.Option("main", "--branch", "-b", help="Git branch to analyze"),
    model: str = typer.Option("qwen2.5-coder", "--model", "-m", help="Ollama LLM model name"),
    ollama_url: str = typer.Option("http://localhost:11434", "--ollama-url", help="Local Ollama server URL"),
    output_dir: str = typer.Option("ci_reports", "--output-dir", "-o", help="Directory for generated reports"),
    docker: bool = typer.Option(True, "--docker/--no-docker", help="Run Docker build validation"),
    ai_review: bool = typer.Option(True, "--ai-review/--no-ai-review", help="Run Ollama AI code review"),
    threat_model: bool = typer.Option(True, "--threat-model/--no-threat-model", help="Run STRIDE threat modeling"),
    auto_fix: bool = typer.Option(False, "--auto-fix/--no-auto-fix", help="Auto-fix violations using AI"),
    write_tests: bool = typer.Option(False, "--write-tests/--no-write-tests", help="Generate pytest test files"),
    min_score: int = typer.Option(75, "--min-score", help="Alert threshold for quality score"),
    max_violations: int = typer.Option(10, "--max-violations", help="Alert threshold for violation count"),
    slack_webhook: str = typer.Option("", "--slack-webhook", help="Slack webhook URL for alerts"),
    save_history: bool = typer.Option(True, "--save-history/--no-save-history", help="Save run to web dashboard history"),
):
    """Executes the full automated DevOps CI audit pipeline."""
    console.print(Panel.fit("[bold cyan]🤖 AI DevOps Assistant Pipeline Initialized[/bold cyan]"))

    # Phase 1: Ingestion & Git Management
    with console.status("[bold green]Phase 1: Ingesting Repository...[/bold green]"):
        git_mgr = GitManager(target_path=path, repo_url=repo, branch=branch)
        work_dir = git_mgr.working_dir
        commit_info = git_mgr.get_commit_info()
        diff = git_mgr.get_diff()
        console.print(f"  ✓ Ingested repo at [yellow]{work_dir}[/yellow] (Commit: [bold]{commit_info.commit_hash}[/bold])")

    # Phase 2: Static Analysis & Security (7 scanners)
    with console.status("[bold green]Phase 2: Running Scanners (Ruff, Bandit, Semgrep, Mypy, Pylint, Safety, Trivy)...[/bold green]"):
        v_ruff = run_ruff(work_dir)
        v_bandit = run_bandit(work_dir)
        v_semgrep = run_semgrep(work_dir)
        v_mypy = run_mypy(work_dir)
        v_pylint = run_pylint(work_dir)
        v_safety = run_safety(work_dir)
        v_trivy = run_trivy(work_dir)
        violations = v_ruff + v_bandit + v_semgrep + v_mypy + v_pylint + v_safety + v_trivy
        console.print(
            f"  ✓ Static Analysis Complete: [bold yellow]{len(violations)}[/bold yellow] issues found "
            f"(Ruff:{len(v_ruff)} Bandit:{len(v_bandit)} Semgrep:{len(v_semgrep)} "
            f"Mypy:{len(v_mypy)} Pylint:{len(v_pylint)} Safety:{len(v_safety)} Trivy:{len(v_trivy)})"
        )

    # Phase 2b: Auto-fix (optional)
    fix_result = None
    if auto_fix and violations:
        with console.status("[bold green]Phase 2b: Auto-fixing violations with AI...[/bold green]"):
            fix_result = run_autofix(work_dir, violations, ollama_url=ollama_url, model=model)
            console.print(f"  ✓ Auto-fix: [green]{len(fix_result['fixed'])}[/green] fixed, "
                          f"[yellow]{len(fix_result['skipped'])}[/yellow] skipped")
            # Re-run scanners after fix
            violations = run_ruff(work_dir) + run_bandit(work_dir) + run_semgrep(work_dir)

    # Phase 3: AI Test Generation & Pytest Execution
    test_result = None
    with console.status("[bold green]Phase 3: Generating & Executing Tests (pytest + Ollama)...[/bold green]"):
        if write_tests:
            generate_tests_for_repo(work_dir, ollama_url=ollama_url, model=model)
        else:
            generate_tests_for_repo(work_dir, ollama_url=ollama_url, model=model)
        test_result = run_pytest(work_dir)
        console.print(f"  ✓ Tests Executed: [bold green]{test_result.passed}/{test_result.total_tests}[/bold green] passed ({test_result.coverage_percentage}% cov)")

    # Phase 4: AI Code Review
    ai_res = None
    if ai_review:
        with console.status("[bold green]Phase 4: Performing AI Code Review (Ollama)...[/bold green]"):
            ai_res = run_ai_code_review(work_dir, git_diff=diff, violations=violations, ollama_url=ollama_url, model=model)
            console.print(f"  ✓ AI Review Score: [bold cyan]{ai_res.quality_score}/100[/bold cyan]")
    else:
        ai_res = run_ai_code_review(work_dir, violations=violations)

    # Phase 4b: Threat Modeling
    threat = None
    if threat_model:
        with console.status("[bold green]Phase 4b: Running STRIDE Threat Model...[/bold green]"):
            threat = run_threat_model(violations, diff, ollama_url=ollama_url, model=model)
            console.print(f"  ✓ Threat Model: [bold magenta]{len(threat.threats)}[/bold magenta] threats identified")

    # Phase 5: Docker Build Validation
    docker_res = None
    if docker:
        with console.status("[bold green]Phase 5: Validating Docker Container Build...[/bold green]"):
            docker_res = validate_docker_build(work_dir)
            status_str = "[bold green]Success[/bold green]" if docker_res.success else "[bold red]Failed[/bold red]"
            console.print(f"  ✓ Docker Validation: {status_str}")
    else:
        docker_res = validate_docker_build(work_dir)

    # Phase 6: Report Generation
    overall_passed = (len([v for v in violations if v.severity == "CRITICAL"]) == 0) and test_result.success and docker_res.success
    report_data = CIReportData(
        commit_info=commit_info,
        target_path=path,
        violations=violations,
        test_result=test_result,
        ai_review=ai_res,
        docker_result=docker_res,
        threat_model=threat,
        overall_passed=overall_passed,
        quality_score=ai_res.quality_score,
    )

    out_path = os.path.abspath(output_dir)
    md_file = generate_markdown_report(report_data, output_dir=out_path)
    html_file = generate_html_report(report_data, output_dir=out_path)

    # Save to web dashboard history
    if save_history:
        try:
            from devops_assistant.web.storage import save_run
            save_run(report_data)
            console.print(f"  ✓ Run [cyan]{report_data.run_id}[/cyan] saved to dashboard history")
        except Exception as e:
            console.print(f"  [yellow]Warning:[/yellow] Could not save to history: {e}")

    # Alerts
    alert_cfg = AlertConfig(
        min_quality_score=min_score,
        max_violations=max_violations,
        slack_webhook=slack_webhook,
    )
    check_and_alert(report_data, alert_cfg)

    git_mgr.cleanup()

    # Console Summary Table
    table = Table(title="CI Pipeline Summary Result")
    table.add_column("Component", style="cyan")
    table.add_column("Result", style="bold")
    table.add_column("Details", style="magenta")

    table.add_row("Static Analysis", f"{len(violations)} violations",
                  f"Ruff:{len(v_ruff)} Bandit:{len(v_bandit)} Mypy:{len(v_mypy)} Pylint:{len(v_pylint)}")
    table.add_row("pytest Unit Tests", f"{test_result.passed}/{test_result.total_tests} passed",
                  f"{test_result.coverage_percentage}% code coverage")
    table.add_row("AI Code Review", f"{ai_res.quality_score}/100 score",
                  ai_res.summary[:60] + "..." if len(ai_res.summary) > 60 else ai_res.summary)
    if threat:
        table.add_row("Threat Model", f"{len(threat.threats)} threats", threat.summary[:60] + "...")
    table.add_row("Docker Build", "Passed" if docker_res.success else "Failed", docker_res.image_tag or "N/A")

    console.print(table)
    console.print(f"\n[bold green]✅ CI Reports Generated:[/bold green]")
    console.print(f"  • Markdown: [link=file://{md_file}]{md_file}[/link]")
    console.print(f"  • HTML Dashboard: [link=file://{html_file}]{html_file}[/link]")
    console.print(f"\n[bold blue]🌐 Web Dashboard:[/bold blue] Run [bold]devops-assistant web[/bold] then open http://localhost:8080")


@app.command("web")
def web_cmd(
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind"),
    port: int = typer.Option(8080, "--port", help="Port to listen on"),
):
    """Start the live web dashboard on http://localhost:8080."""
    from devops_assistant.web import start_web_server
    console.print(Panel.fit(f"[bold cyan]🌐 Starting Web Dashboard on http://{host}:{port}[/bold cyan]"))
    start_web_server(host=host, port=port)


@app.command("generate-ci")
def generate_ci_cmd(
    platform: str = typer.Argument("github", help="CI platform: github | gitlab | pre-commit"),
    target: str = typer.Option(".", "--target", "-t", help="Target project directory"),
    model: str = typer.Option("qwen2.5-coder", "--model", "-m", help="Ollama model to use in CI"),
):
    """Generate CI/CD workflow files for github, gitlab, or pre-commit."""
    if platform == "github":
        path = generate_github_actions(output_dir=target, model=model)
        console.print(f"  ✓ [green]GitHub Actions workflow:[/green] {path}")
    elif platform == "gitlab":
        path = generate_gitlab_ci(output_dir=target, model=model)
        console.print(f"  ✓ [green]GitLab CI pipeline:[/green] {path}")
    elif platform == "pre-commit":
        path = generate_pre_commit_hook(output_dir=target)
        console.print(f"  ✓ [green]Pre-commit hook:[/green] {path}")
    else:
        console.print(f"[red]Unknown platform:[/red] {platform}. Use: github | gitlab | pre-commit")
        raise typer.Exit(1)


@app.command("lint")
def lint_cmd(target: str = typer.Argument(".", help="Directory to scan")):
    """Run all static scanners on target directory."""
    console.print(f"[bold cyan]Scanning directory {target}...[/bold cyan]")
    v_ruff = run_ruff(target)
    v_bandit = run_bandit(target)
    v_semgrep = run_semgrep(target)
    v_mypy = run_mypy(target)
    v_safety = run_safety(target)
    all_v = v_ruff + v_bandit + v_semgrep + v_mypy + v_safety
    console.print(f"[bold green]Scan complete.[/bold green] Found {len(all_v)} total violations.")
    for v in all_v[:15]:
        console.print(f"  [{v.severity}] {v.scanner_name} | {v.file_path}:{v.line_number} -> {v.description}")


@app.command("mcp")
def mcp_cmd():
    """Start standard Stdio MCP server interface."""
    start_mcp_server()


if __name__ == "__main__":
    app()
