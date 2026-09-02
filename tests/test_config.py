"""
Unit tests for configuration data models.
"""

from devops_assistant.config import Violation, Severity, TestRunResult, AIReviewResult, DockerBuildResult, CIReportData


def test_violation_model():
    v = Violation(
        scanner_name="Ruff",
        file_path="main.py",
        line_number=10,
        rule_id="E501",
        description="Line too long",
        severity=Severity.LOW
    )
    assert v.scanner_name == "Ruff"
    assert v.line_number == 10
    assert v.severity == Severity.LOW


def test_test_run_result_success():
    res = TestRunResult(total_tests=5, passed=5, failed=0, coverage_percentage=88.5)
    assert res.success is True

    f_res = TestRunResult(total_tests=5, passed=4, failed=1)
    assert f_res.success is False


def test_ci_report_data():
    report = CIReportData(target_path=".")
    assert report.overall_passed is True
    assert report.quality_score == 100
    assert report.commit_info.branch == "main"
