"""
Semgrep Static Analysis Integration.
"""

import json
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity


def run_semgrep(target_path: str) -> List[Violation]:
    """Runs Semgrep static code analysis and parses violations."""
    violations: List[Violation] = []
    cmd = ["semgrep", "scan", "--config", "auto", "--json", target_path]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
        if res.stdout:
            data = json.loads(res.stdout)
            results = data.get("results", [])
            for item in results:
                check_id = item.get("check_id", "SEMGREP")
                extra = item.get("extra", {})
                message = extra.get("message", "Semgrep rule violation")
                path = item.get("path", "unknown")
                start = item.get("start", {})
                line = start.get("line", 1)
                s_severity = str(extra.get("severity", "WARNING")).upper()

                severity = Severity.MEDIUM
                if s_severity in ["ERROR", "CRITICAL", "HIGH"]:
                    severity = Severity.HIGH
                elif s_severity in ["INFO", "LOW"]:
                    severity = Severity.LOW

                violations.append(
                    Violation(
                        scanner_name="Semgrep",
                        file_path=path,
                        line_number=line,
                        rule_id=check_id,
                        description=message,
                        severity=severity,
                    )
                )
    except FileNotFoundError:
        # Semgrep binary not installed
        pass
    except subprocess.TimeoutExpired:
        print("[Warning] Semgrep scan timed out.")
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"[Warning] Semgrep scanner error: {e}")

    return violations
