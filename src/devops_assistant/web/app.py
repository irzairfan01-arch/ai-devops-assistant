"""
Flask Web Dashboard for AI DevOps Assistant.
Provides live pipeline execution, real-time SSE streaming, and run history.
"""

import json
import queue
import threading
import sys
import os

from flask import Flask, render_template, request, Response, jsonify, redirect, url_for

# Ensure devops_assistant package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from devops_assistant.web.storage import save_run, get_run, list_runs, delete_run, get_trend_data
from devops_assistant.config import PipelineConfig

# Always resolve templates from the actual source directory on disk
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
app = Flask(__name__, template_folder=_TEMPLATE_DIR)
app.secret_key = "devops-assistant-secret"
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Global SSE queue per run_id
_sse_queues: dict[str, queue.Queue] = {}


def _run_pipeline_thread(config: PipelineConfig, run_q: queue.Queue):
    """Run the full pipeline in a background thread, emitting SSE events."""
    from devops_assistant.git_manager import GitManager
    from devops_assistant.scanners import run_ruff, run_bandit, run_semgrep, run_mypy, run_safety
    from devops_assistant.test_engine import run_pytest, generate_tests_for_repo
    from devops_assistant.ai_review import run_ai_code_review
    from devops_assistant.ai_review.threat_model import run_threat_model
    from devops_assistant.docker_engine import validate_docker_build
    from devops_assistant.config import CIReportData

    def emit(phase: str, msg: str, status: str = "running"):
        run_q.put(json.dumps({"phase": phase, "msg": msg, "status": status}))

    try:
        emit("git", "Ingesting repository...", "running")
        git_mgr = GitManager(target_path=config.target_path, repo_url=config.repo_url, branch=config.branch)
        work_dir = git_mgr.working_dir
        commit_info = git_mgr.get_commit_info()
        diff = git_mgr.get_diff()
        emit("git", f"Ingested: {commit_info.commit_hash} ({commit_info.branch})", "done")

        emit("scan", "Running linters (Ruff, Bandit, Semgrep, Mypy, Safety)...", "running")
        violations = (run_ruff(work_dir) + run_bandit(work_dir) +
                      run_semgrep(work_dir) + run_mypy(work_dir) + run_safety(work_dir))
        emit("scan", f"{len(violations)} violations found.", "done")

        emit("tests", "Generating & running tests...", "running")
        generate_tests_for_repo(work_dir, config.ollama_url, config.ollama_model)
        test_result = run_pytest(work_dir)
        emit("tests", f"{test_result.passed}/{test_result.total_tests} passed, {test_result.coverage_percentage}% coverage", "done")

        emit("ai", "Running AI code review...", "running")
        ai_res = run_ai_code_review(work_dir, git_diff=diff, violations=violations,
                                    ollama_url=config.ollama_url, model=config.ollama_model)
        emit("ai", f"AI Score: {ai_res.quality_score}/100", "done")

        emit("threat", "Building STRIDE threat model...", "running")
        threat = run_threat_model(violations, diff, config.ollama_url, config.ollama_model)
        emit("threat", f"{len(threat.threats)} threats identified.", "done")

        emit("docker", "Validating Docker build...", "running")
        docker_res = validate_docker_build(work_dir)
        emit("docker", "Passed" if docker_res.success else "Failed", "done" if docker_res.success else "error")

        overall_passed = (len([v for v in violations if v.severity == "CRITICAL"]) == 0
                          and test_result.success and docker_res.success)

        report = CIReportData(
            commit_info=commit_info,
            target_path=config.target_path,
            violations=violations,
            test_result=test_result,
            ai_review=ai_res,
            docker_result=docker_res,
            threat_model=threat,
            overall_passed=overall_passed,
            quality_score=ai_res.quality_score,
        )
        save_run(report)
        git_mgr.cleanup()

        emit("done", report.run_id, "complete")
    except Exception as e:
        import traceback
        with open("C:\\Users\\irzai\\.gemini\\ai_devops_assistant\\error_log.txt", "w") as f:
            f.write(traceback.format_exc())
        emit("error", str(e), "error")
    finally:
        run_q.put(None)  # Sentinel


@app.route("/")
def index():
    runs = list_runs()
    return render_template("index.html", runs=runs)


@app.route("/run", methods=["POST"])
def trigger_run():
    target_path = request.form.get("target_path", ".")
    model = request.form.get("model", "qwen2.5-coder")
    ollama_url = request.form.get("ollama_url", "http://localhost:11434")

    import uuid
    run_id = str(uuid.uuid4())[:8]
    q: queue.Queue = queue.Queue()
    _sse_queues[run_id] = q

    config = PipelineConfig(
        target_path=target_path,
        ollama_model=model,
        ollama_url=ollama_url,
    )

    t = threading.Thread(target=_run_pipeline_thread, args=(config, q), daemon=True)
    t.start()

    return redirect(url_for("stream_view", run_id=run_id))


@app.route("/stream/<run_id>")
def stream_view(run_id: str):
    return render_template("stream.html", run_id=run_id)


@app.route("/stream/events/<run_id>")
def stream_events(run_id: str):
    """SSE endpoint — streams pipeline progress."""
    def generate():
        q = _sse_queues.get(run_id)
        if not q:
            yield "data: {\"phase\": \"error\", \"msg\": \"Run not found\", \"status\": \"error\"}\n\n"
            return
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {item}\n\n"
        _sse_queues.pop(run_id, None)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/report/<run_id>")
def report_view(run_id: str):
    report = get_run(run_id)
    if not report:
        return "Report not found", 404
    return render_template("report.html", report=report)


@app.route("/history")
def history_view():
    runs = list_runs()
    trend = get_trend_data()
    return render_template("history.html", runs=runs, trend=json.dumps(trend))


@app.route("/api/history")
def api_history():
    return jsonify(list_runs())


@app.route("/api/trend")
def api_trend():
    return jsonify(get_trend_data())


@app.route("/api/run/<run_id>", methods=["DELETE"])
def api_delete_run(run_id: str):
    delete_run(run_id)
    return jsonify({"status": "deleted"})


def start_web_server(host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
    """Start the Flask web server."""
    app.run(host=host, port=port, debug=debug, threaded=True)
