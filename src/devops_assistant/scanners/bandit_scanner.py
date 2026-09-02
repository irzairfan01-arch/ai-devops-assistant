"""
Bandit Security AST Scanner Integration.
"""

import json
import sys
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity


def run_bandit(target_path: str) -> List[Violation]:
    """Runs Bandit AST security check on Python files and parses violations."""
    violations: List[Violation] = []
    cmd = ["bandit", "-r", target_path, "-f", "json", "-q"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        cmd = [sys.executable, "-m", "bandit", "-r", target_path, "-f", "json", "-q"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return violations

    try:
        if res.stdout:
            data = json.loads(res.stdout)
            results = data.get("results", [])
            for item in results:
                test_id = item.get("test_id", "BANDIT")
                issue_text = item.get("issue_text", "Security issue detected")
                filename = item.get("filename", "unknown")
                line_number = item.get("line_number", 1)
                b_severity = str(item.get("issue_severity", "MEDIUM")).upper()

                severity = Severity.MEDIUM
                if b_severity == "HIGH":
                    severity = Severity.HIGH
                elif b_severity == "LOW":
                    severity = Severity.LOW

                violations.append(
                    Violation(
                        scanner_name="Bandit",
                        file_path=filename,
                        line_number=line_number,
                        rule_id=test_id,
                        description=issue_text,
                        severity=severity,
                    )
                )
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"[Warning] Bandit scanner error: {e}")

    return violations
