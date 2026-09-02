"""
Pylint Code Quality Scanner Integration.
"""

import json
import sys
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity

# Pylint message type -> Severity mapping
_PYLINT_SEVERITY = {
    "C": Severity.LOW,       # Convention
    "R": Severity.LOW,       # Refactor
    "W": Severity.MEDIUM,    # Warning
    "E": Severity.HIGH,      # Error
    "F": Severity.CRITICAL,  # Fatal
}


def run_pylint(target_path: str) -> List[Violation]:
    """Runs pylint on target directory and parses JSON violations."""
    violations: List[Violation] = []
    cmd = ["pylint", target_path, "--output-format=json",
           "--recursive=y", "--disable=C0114,C0115,C0116"]  # skip missing docstring warnings

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        cmd = [sys.executable, "-m", "pylint", target_path, "--output-format=json",
               "--recursive=y", "--disable=C0114,C0115,C0116"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return violations

    try:
        if res.stdout:
            data = json.loads(res.stdout)
            for item in data:
                msg_id = item.get("message-id", "PYLINT")
                # First char of message-id is the category letter
                category_char = msg_id[0].upper() if msg_id else "W"
                severity = _PYLINT_SEVERITY.get(category_char, Severity.MEDIUM)

                violations.append(
                    Violation(
                        scanner_name="Pylint",
                        file_path=item.get("path", "unknown"),
                        line_number=item.get("line", 1),
                        rule_id=msg_id,
                        description=item.get("message", "Pylint issue"),
                        severity=severity,
                    )
                )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    except Exception as e:
        print(f"[Warning] Pylint scanner error: {e}")

    return violations
