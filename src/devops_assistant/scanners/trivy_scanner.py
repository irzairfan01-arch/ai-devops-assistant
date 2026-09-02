"""
Trivy Filesystem Vulnerability Scanner Integration.
"""

import json
import subprocess
from typing import List
from devops_assistant.config import Violation, Severity

_TRIVY_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "HIGH": Severity.HIGH,
    "MEDIUM": Severity.MEDIUM,
    "LOW": Severity.LOW,
    "UNKNOWN": Severity.INFO,
}


def run_trivy(target_path: str) -> List[Violation]:
    """Runs trivy filesystem scan on target directory and parses vulnerabilities."""
    violations: List[Violation] = []

    cmd = [
        "trivy", "fs", "--format", "json",
        "--quiet", "--scanners", "vuln,secret,config",
        target_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    except FileNotFoundError:
        # Trivy not installed — silently skip
        return violations
    except subprocess.TimeoutExpired:
        print("[Warning] Trivy scan timed out.")
        return violations

    try:
        if not res.stdout:
            return violations

        data = json.loads(res.stdout)
        results = data.get("Results", [])

        for result in results:
            target_file = result.get("Target", "unknown")
            vulnerabilities = result.get("Vulnerabilities") or []
            misconfigs = result.get("Misconfigurations") or []
            secrets = result.get("Secrets") or []

            for vuln in vulnerabilities:
                sev_str = vuln.get("Severity", "UNKNOWN").upper()
                severity = _TRIVY_SEVERITY.get(sev_str, Severity.MEDIUM)
                pkg = vuln.get("PkgName", "unknown")
                cve = vuln.get("VulnerabilityID", "TRIVY-UNKNOWN")
                title = vuln.get("Title") or vuln.get("Description") or "Vulnerability found"
                installed = vuln.get("InstalledVersion", "")
                fixed = vuln.get("FixedVersion", "")
                desc = f"[{pkg} {installed}] {title}"
                if fixed:
                    desc += f" (fix: {fixed})"

                violations.append(Violation(
                    scanner_name="Trivy",
                    file_path=target_file,
                    line_number=1,
                    rule_id=cve,
                    description=desc,
                    severity=severity,
                ))

            for mc in misconfigs:
                sev_str = mc.get("Severity", "UNKNOWN").upper()
                severity = _TRIVY_SEVERITY.get(sev_str, Severity.MEDIUM)
                violations.append(Violation(
                    scanner_name="Trivy",
                    file_path=target_file,
                    line_number=mc.get("CauseMetadata", {}).get("StartLine", 1),
                    rule_id=mc.get("ID", "TRIVY-MISC"),
                    description=mc.get("Title", "Misconfiguration found"),
                    severity=severity,
                ))

            for secret in secrets:
                violations.append(Violation(
                    scanner_name="Trivy",
                    file_path=target_file,
                    line_number=secret.get("StartLine", 1),
                    rule_id=f"SECRET-{secret.get('RuleID', 'unknown')}",
                    description=f"Secret detected: {secret.get('Title', 'Unknown secret')}",
                    severity=Severity.CRITICAL,
                ))

    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    except Exception as e:
        print(f"[Warning] Trivy scanner error: {e}")

    return violations
