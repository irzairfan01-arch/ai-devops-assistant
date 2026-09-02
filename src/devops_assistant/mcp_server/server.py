"""
Model Context Protocol (MCP) Stdio JSON-RPC 2.0 Server.
Exposes DevOps capabilities as standard tools to AI agents and IDEs.
"""

import sys
import json
from typing import Dict, Any
from devops_assistant.scanners import run_ruff, run_bandit, run_semgrep
from devops_assistant.test_engine import run_pytest, generate_tests_for_repo
from devops_assistant.docker_engine import validate_docker_build
from devops_assistant.ai_review import run_ai_code_review
from devops_assistant.git_manager import GitManager
from devops_assistant.config import CIReportData
from devops_assistant.reporter import generate_markdown_report, generate_html_report


TOOLS_DEFINITIONS = [
    {
        "name": "devops_run_lint",
        "description": "Run Ruff, Bandit, and Semgrep static linters and security scanners on target directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "default": "."}
            }
        }
    },
    {
        "name": "devops_run_pytest",
        "description": "Execute pytest suite and collect coverage stats.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "default": "."}
            }
        }
    },
    {
        "name": "devops_generate_tests",
        "description": "Use local Ollama model to generate pytest unit tests for source files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "default": "."},
                "ollama_url": {"type": "string", "default": "http://localhost:11434"},
                "model": {"type": "string", "default": "qwen2.5-coder"}
            }
        }
    },
    {
        "name": "devops_build_docker",
        "description": "Validate containerization build for detected Dockerfile.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "default": "."}
            }
        }
    },
    {
        "name": "devops_full_ci_pipeline",
        "description": "Execute end-to-end automated DevOps CI pipeline (Clone, Lint, Test, AI Review, Docker, Report).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_url": {"type": "string"},
                "target_path": {"type": "string", "default": "."},
                "ollama_url": {"type": "string", "default": "http://localhost:11434"},
                "model": {"type": "string", "default": "qwen2.5-coder"}
            }
        }
    }
]


def handle_tool_call(name: str, args: Dict[str, Any]) -> str:
    """Executes requested tool and returns JSON string result."""
    target_path = args.get("target_path", ".")
    
    if name == "devops_run_lint":
        v_ruff = run_ruff(target_path)
        v_bandit = run_bandit(target_path)
        v_semgrep = run_semgrep(target_path)
        all_violations = v_ruff + v_bandit + v_semgrep
        return json.dumps([v.model_dump() for v in all_violations], indent=2)

    elif name == "devops_run_pytest":
        res = run_pytest(target_path)
        return json.dumps(res.model_dump(), indent=2)

    elif name == "devops_generate_tests":
        ollama_url = args.get("ollama_url", "http://localhost:11434")
        model = args.get("model", "qwen2.5-coder")
        res = generate_tests_for_repo(target_path, ollama_url=ollama_url, model=model)
        if res:
            return json.dumps(res.model_dump(), indent=2)
        return json.dumps({"status": "skipped", "message": "Ollama offline or no python files found"})

    elif name == "devops_build_docker":
        res = validate_docker_build(target_path)
        return json.dumps(res.model_dump(), indent=2)

    elif name == "devops_full_ci_pipeline":
        repo_url = args.get("repo_url")
        git_mgr = GitManager(target_path=target_path, repo_url=repo_url)
        work_dir = git_mgr.working_dir
        commit_info = git_mgr.get_commit_info()
        diff = git_mgr.get_diff()

        violations = run_ruff(work_dir) + run_bandit(work_dir) + run_semgrep(work_dir)
        test_res = run_pytest(work_dir)
        ai_res = run_ai_code_review(work_dir, git_diff=diff, violations=violations)
        docker_res = validate_docker_build(work_dir)

        overall_passed = (len([v for v in violations if v.severity == "CRITICAL"]) == 0) and test_res.success and docker_res.success
        report_data = CIReportData(
            commit_info=commit_info,
            target_path=target_path,
            violations=violations,
            test_result=test_res,
            ai_review=ai_res,
            docker_result=docker_res,
            overall_passed=overall_passed,
            quality_score=ai_res.quality_score
        )

        md_path = generate_markdown_report(report_data, output_dir=os.path.join(work_dir, "ci_reports"))
        html_path = generate_html_report(report_data, output_dir=os.path.join(work_dir, "ci_reports"))

        result = {
            "overall_passed": overall_passed,
            "quality_score": report_data.quality_score,
            "violations_count": len(violations),
            "markdown_report": md_path,
            "html_report": html_path
        }
        git_mgr.cleanup()
        return json.dumps(result, indent=2)

    raise ValueError(f"Unknown tool: {name}")


def start_mcp_server():
    """Runs standard MCP stdio JSON-RPC loop."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "ai-devops-assistant", "version": "0.1.0"}
                    }
                }
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": TOOLS_DEFINITIONS}
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                content_text = handle_tool_call(tool_name, arguments)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": content_text}]
                    }
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"}
                }

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
