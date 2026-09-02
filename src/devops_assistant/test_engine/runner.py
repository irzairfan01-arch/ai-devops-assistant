"""
pytest Runner & Coverage Parser Module.
"""

import os
import sys
import time
import json
import xml.etree.ElementTree as ET
import subprocess
from devops_assistant.config import TestRunResult


def run_pytest(target_path: str, test_dir: str = ".") -> TestRunResult:
    """Runs pytest on target repository and returns parsed TestRunResult."""
    start_time = time.time()
    junit_xml_path = os.path.join(target_path, ".pytest_report.xml")
    cov_json_path = os.path.join(target_path, ".coverage.json")

    cmd = [
        "pytest",
        test_dir,
        f"--junitxml={junit_xml_path}",
        "--cov=.",
        f"--cov-report=json:{cov_json_path}",
        "-v"
    ]

    try:
        res = subprocess.run(cmd, cwd=target_path, capture_output=True, text=True, timeout=60, check=False)
    except FileNotFoundError:
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_dir,
            f"--junitxml={junit_xml_path}",
            "--cov=.",
            f"--cov-report=json:{cov_json_path}",
            "-v"
        ]
        try:
            res = subprocess.run(cmd, cwd=target_path, capture_output=True, text=True, timeout=60, check=False)
        except FileNotFoundError:
            return TestRunResult(
                total_tests=0,
                output_log="pytest command not found in current environment.",
                error_details="pytest not installed"
            )

    try:
        duration = round(time.time() - start_time, 2)

        total = 0
        passed = 0
        failed = 0
        skipped = 0
        coverage = 0.0

        # Parse JUnit XML
        if os.path.exists(junit_xml_path):
            try:
                tree = ET.parse(junit_xml_path)
                root = tree.getroot()
                # Could be <testsuites> or <testsuite>
                suite = root if root.tag == "testsuite" else root.find("testsuite")
                if suite is not None:
                    total = int(suite.attrib.get("tests", 0))
                    failed = int(suite.attrib.get("failures", 0)) + int(suite.attrib.get("errors", 0))
                    skipped = int(suite.attrib.get("skipped", 0))
                    passed = max(0, total - failed - skipped)
            except Exception as e:
                print(f"[Warning] Failed parsing JUnit XML: {e}")

        # Fallback to output parsing if total still 0
        if total == 0 and res.stdout:
            for line in res.stdout.splitlines():
                if "passed" in line or "failed" in line:
                    if "passed" in line:
                        passed = 1
                        total += 1
                    if "failed" in line:
                        failed = 1
                        total += 1

        # Parse coverage json if created
        if os.path.exists(cov_json_path):
            try:
                with open(cov_json_path, "r", encoding="utf-8") as f:
                    cov_data = json.load(f)
                    totals = cov_data.get("totals", {})
                    coverage = round(float(totals.get("percent_covered", 0.0)), 1)
            except Exception:
                pass

        # Cleanup temporary report files
        for fpath in [junit_xml_path, cov_json_path]:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

        return TestRunResult(
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_seconds=duration,
            coverage_percentage=coverage,
            output_log=res.stdout + ("\n" + res.stderr if res.stderr else "")
        )

    except FileNotFoundError:
        return TestRunResult(
            total_tests=0,
            output_log="pytest command not found in current environment.",
            error_details="pytest not installed"
        )
    except subprocess.TimeoutExpired:
        return TestRunResult(
            total_tests=0,
            output_log="pytest execution timed out after 60 seconds.",
            error_details="TimeoutExpired"
        )
    except Exception as e:
        return TestRunResult(
            total_tests=0,
            output_log=f"pytest execution failed: {e}",
            error_details=str(e)
        )
