"""
Safety CVE Dependency Vulnerability Scanner Integration.
"""

import json
import sys
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity

# Safety severity strings -> our Severity enum
_SAFETY_SEVERITY = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
}


def run_safety(target_path: str) -> List[Violation]:
    """Runs safety check on requirements.txt to detect known CVEs."""
    violations: List[Violation] = []

    # Try to find requirements.txt
    import os
    req_file = None
    for fname in ["requirements.txt", "requirements/base.txt", "requirements/prod.txt"]:
        candidate = os.path.join(target_path, fname)
        if os.path.isfile(candidate):
            req_file = candidate
            break

    if not req_file:
        return violations  # No requirements to scan

    cmd = ["safety", "check", "-r", req_file, "--json", "--disable-optional-telemetry"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        cmd = [sys.executable, "-m", "safety", "check", "-r", req_file, "--json",
               "--disable-optional-telemetry"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return violations

    try:
        output = res.stdout or res.stderr
        if not output:
            return violations

        # Safety JSON output: list of vulnerability objects
        data = json.loads(output)

        # Handle both old and new safety CLI output formats
        vulns = []
        if isinstance(data, list):
            vulns = data
        elif isinstance(data, dict):
            vulns = data.get("vulnerabilities", [])

        for item in vulns:
            # New format
            pkg = item.get("package_name") or item.get("package") or "unknown"
            cve = item.get("CVE") or item.get("vulnerability_id") or "CVE-UNKNOWN"
            desc = item.get("advisory") or item.get("description") or "Known vulnerability"
            sev_str = str(item.get("severity", "medium")).lower()
            severity = _SAFETY_SEVERITY.get(sev_str, Severity.MEDIUM)

            violations.append(
                Violation(
                    scanner_name="Safety",
                    file_path=req_file,
                    line_number=1,
                    rule_id=cve,
                    description=f"[{pkg}] {desc}",
                    severity=severity,
                )
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    except Exception as e:
        print(f"[Warning] Safety scanner error: {e}")

    return violations
