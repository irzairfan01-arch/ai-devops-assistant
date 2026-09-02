"""
Mypy Static Type Checker Integration.
"""

import re
import sys
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity


def run_mypy(target_path: str) -> List[Violation]:
    """Runs mypy type checker on target directory and parses violations."""
    violations: List[Violation] = []
    cmd = ["mypy", target_path, "--no-error-summary", "--show-column-numbers",
           "--ignore-missing-imports", "--no-color-output"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        cmd = [sys.executable, "-m", "mypy", target_path,
               "--no-error-summary", "--show-column-numbers",
               "--ignore-missing-imports", "--no-color-output"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return violations

    # mypy output format: filename:line:col: error: message  [error-code]
    pattern = re.compile(r"^(.+?):(\d+):\d+: (\w+): (.+?)(?:\s+\[(.+)\])?$")

    for line in res.stdout.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue

        filepath, lineno, level, message, code = m.groups()
        code = code or "mypy"

        if level == "error":
            severity = Severity.HIGH
        elif level == "warning":
            severity = Severity.MEDIUM
        else:
            severity = Severity.LOW

        violations.append(
            Violation(
                scanner_name="Mypy",
                file_path=filepath,
                line_number=int(lineno),
                rule_id=code,
                description=message,
                severity=severity,
            )
        )

    return violations
