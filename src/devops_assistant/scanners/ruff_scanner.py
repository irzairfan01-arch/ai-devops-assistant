"""
Ruff Python Code Linter Integration.
"""

import json
import sys
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity


def run_ruff(target_path: str) -> List[Violation]:
    """Runs ruff check on target directory and parses JSON violations."""
    violations: List[Violation] = []
    cmd = ["ruff", "check", "--output-format", "json", target_path]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        cmd = [sys.executable, "-m", "ruff", "check", "--output-format", "json", target_path]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return violations

    try:
        if res.stdout:
            data = json.loads(res.stdout)
            for item in data:
                code = item.get("code", "RUFF")
                message = item.get("message", "Lint issue")
                filename = item.get("filename", "unknown")
                location = item.get("location", {})
                line = location.get("row", 1)

                # Determine severity based on ruff code prefix
                severity = Severity.LOW
                if code.startswith("E9") or code.startswith("F"):
                    severity = Severity.HIGH
                elif code.startswith("E") or code.startswith("W"):
                    severity = Severity.MEDIUM

                violations.append(
                    Violation(
                        scanner_name="Ruff",
                        file_path=filename,
                        line_number=line,
                        rule_id=code,
                        description=message,
                        severity=severity,
                    )
                )
    except FileNotFoundError:
        # Ruff binary not found
        pass
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"[Warning] Ruff scanner error: {e}")

    return violations
