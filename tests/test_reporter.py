"""
Unit tests for report generator modules.
"""

import os
import tempfile
from devops_assistant.config import CIReportData, Violation, Severity
from devops_assistant.reporter import generate_markdown_report, generate_html_report


def test_markdown_and_html_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        v = Violation(
            scanner_name="Bandit",
            file_path="auth.py",
            line_number=15,
            rule_id="B105",
            description="Hardcoded password string",
            severity=Severity.HIGH
        )
        data = CIReportData(violations=[v], target_path=tmpdir)

        md_path = generate_markdown_report(data, output_dir=tmpdir)
        html_path = generate_html_report(data, output_dir=tmpdir)

        assert os.path.exists(md_path)
        assert os.path.exists(html_path)

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Hardcoded password string" in content
            assert "B105" in content

        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            assert "Hardcoded password string" in html_content
            assert "AI DevOps Assistant" in html_content
