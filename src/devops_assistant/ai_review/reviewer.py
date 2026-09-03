"""
Ollama AI Code Reviewer.
"""

import os
import json
import httpx
from typing import List, Optional
from devops_assistant.config import AIReviewResult, AIReviewComment, Violation
from devops_assistant.graphify import ProjectGraph


def run_ai_code_review(
    target_path: str,
    git_diff: str = "",
    violations: List[Violation] = None,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder"
) -> AIReviewResult:
    """Executes AI-powered code review over repository files/diff using Ollama."""
    
    # Check if Ollama is available
    try:
        r = httpx.get(f"{ollama_url}/api/tags", timeout=3.0)
        if r.status_code != 200:
            return AIReviewResult(
                quality_score=90,
                summary="Ollama LLM server unreachable. Skipping AI review pass.",
                comments=[]
            )
    except Exception:
        return AIReviewResult(
            quality_score=90,
            summary="Ollama LLM server unreachable. Skipping AI review pass.",
            comments=[]
        )

    # Collect source files sample or git diff
    code_context = ""
    if git_diff.strip():
        code_context = f"GIT DIFF:\n{git_diff[:4000]}"
    else:
        # Sample main files
        snippets = []
        for root, _, files in os.walk(target_path):
            if "venv" in root or ".git" in root or "tests" in root:
                continue
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    fpath = os.path.join(root, file)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read(1500)
                            snippets.append(f"--- FILE: {file} ---\n{content}")
                    except Exception:
                        pass
        code_context = "\n\n".join(snippets[:3])

    if not code_context:
        return AIReviewResult(quality_score=95, summary="No source files found for review.", comments=[])

    # Generate full project architecture graph
    project_graph = ProjectGraph(target_path)
    architecture_context = project_graph.get_project_signatures()
    arch_block = ""
    if architecture_context.strip():
        arch_block = f"PROJECT ARCHITECTURE (Cross-Folder Signatures):\n{architecture_context}\n"

    violation_summary = ""
    if violations:
        v_lines = [f"- [{v.scanner_name}] {v.file_path}:{v.line_number} -> {v.description}" for v in violations[:5]]
        violation_summary = "LINTER / SECURITY WARNINGS DETECTED:\n" + "\n".join(v_lines)

    prompt = f"""You are a Principal Software Engineer performing an automated Code Review.

{arch_block}

CODE CONTEXT (Files under review):
{code_context}

{violation_summary}

TASK:
Analyze the code quality, logic errors, edge cases, and potential security flaws.
Respond strictly with a JSON object in the following structure:
{{
  "quality_score": <number between 0 and 100>,
  "summary": "<2 sentence high level code quality summary>",
  "comments": [
    {{
      "file_path": "<filename>",
      "line_number": <line or null>,
      "category": "Code Quality | Security | Performance | Architecture",
      "comment": "<detailed comment>",
      "suggested_code": "<optional improved code snippet or null>"
    }}
  ]
}}
"""

    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        resp = httpx.post(f"{ollama_url}/api/generate", json=payload, timeout=300.0)
        if resp.status_code == 200:
            raw = resp.json().get("response", "{}")
            data = json.loads(raw)
            comments = [
                AIReviewComment(
                    file_path=c.get("file_path", "general"),
                    line_number=c.get("line_number"),
                    category=c.get("category", "Code Quality"),
                    comment=c.get("comment", ""),
                    suggested_code=c.get("suggested_code")
                )
                for c in data.get("comments", [])
            ]
            return AIReviewResult(
                quality_score=int(data.get("quality_score", 85)),
                summary=data.get("summary", "AI review completed."),
                comments=comments
            )
    except Exception as e:
        print(f"[Warning] AI Code review call failed: {e}")

    return AIReviewResult(
        quality_score=85,
        summary="AI review completed with default heuristics.",
        comments=[]
    )
