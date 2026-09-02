"""
AI-Powered Auto-Fix Engine.
Uses Ollama to generate code fixes for violations and applies them safely with backups.
"""

import os
import shutil
import difflib
import httpx
import subprocess
from typing import List, Optional
from devops_assistant.config import Violation, AIReviewComment


def _build_fix_prompt(file_content: str, violation: Violation) -> str:
    """Build a prompt asking Ollama to fix a specific violation."""
    return f"""You are an expert Python developer. Fix the following code issue.

FILE: {violation.file_path}
LINE: {violation.line_number}
RULE: {violation.rule_id}
ISSUE: {violation.description}

ORIGINAL CODE:
```python
{file_content}
```

Return ONLY the corrected Python code with no explanation, no markdown fences, no comments about what changed.
Output the complete fixed file content only."""


def _apply_fix(original_path: str, fixed_content: str) -> bool:
    """Write fixed content to file after creating a .bak backup."""
    backup_path = original_path + ".bak"
    try:
        shutil.copy2(original_path, backup_path)
        with open(original_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        return True
    except Exception as e:
        print(f"[Warning] Could not apply fix to {original_path}: {e}")
        return False


def run_autofix(
    target_path: str,
    violations: List[Violation],
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder",
    dry_run: bool = False,
    commit_fixes: bool = True,
) -> dict:
    """
    Attempt to auto-fix violations using Ollama.

    Args:
        target_path: Root directory of the project.
        violations: List of violations to attempt fixing.
        ollama_url: Ollama API URL.
        model: Ollama model name.
        dry_run: If True, compute diffs but don't write files.
        commit_fixes: If True, create a git commit for the fixed files.

    Returns:
        Dict with keys: fixed (list of paths), skipped (list), diffs (dict path->diff)
    """
    result = {"fixed": [], "skipped": [], "diffs": {}}

    # Group violations by file
    by_file: dict = {}
    for v in violations:
        # Skip violations without a real file path
        if not v.file_path or not os.path.isfile(v.file_path):
            result["skipped"].append(v.file_path)
            continue
        by_file.setdefault(v.file_path, []).append(v)

    for file_path, file_violations in by_file.items():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original = f.read()
        except Exception:
            result["skipped"].append(file_path)
            continue

        # Use the first (most severe) violation as the fix target per file
        primary = sorted(file_violations, key=lambda v: v.severity, reverse=True)[0]
        prompt = _build_fix_prompt(original, primary)

        try:
            resp = httpx.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=300.0,
            )
            resp.raise_for_status()
            fixed_content = resp.json().get("response", "").strip()
        except Exception as e:
            print(f"[Warning] Auto-fix call failed for {file_path}: {e}")
            result["skipped"].append(file_path)
            continue

        if not fixed_content:
            result["skipped"].append(file_path)
            continue

        # Compute unified diff
        diff = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
        ))
        result["diffs"][file_path] = diff

        if not dry_run:
            if _apply_fix(file_path, fixed_content):
                result["fixed"].append(file_path)
                print(f"  ✓ Auto-fixed: {file_path} (backup at {file_path}.bak)")
            else:
                result["skipped"].append(file_path)
        else:
            print(f"  [dry-run] Would fix: {file_path}")
            result["fixed"].append(file_path)

    if not dry_run and commit_fixes and result["fixed"]:
        try:
            subprocess.run(["git", "add"] + result["fixed"], cwd=target_path, check=True)
            commit_msg = f"Auto-fix: applied {len(result['fixed'])} AI suggested fixes"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=target_path, check=True)
            print("  ✓ Created git commit for auto-fixes")
        except subprocess.CalledProcessError as e:
            print(f"[Warning] Failed to commit auto-fixes: {e}")
        except FileNotFoundError:
            pass # Git not available

    return result
