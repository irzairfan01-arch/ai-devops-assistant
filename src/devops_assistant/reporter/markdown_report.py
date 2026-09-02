"""
Markdown CI Report Generator.
"""

import os
from devops_assistant.config import CIReportData


def generate_markdown_report(report_data: CIReportData, output_dir: str = "ci_reports") -> str:
    """Renders CI report in Markdown format and saves to file."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "ci_report.md")

    status_icon = "✅ PASSED" if report_data.overall_passed else "❌ FAILED"
    
    md_content = f"""# 🚀 AI DevOps Assistant — Automated CI/CD Audit Report

> **Execution Time**: `{report_data.timestamp}`  
> **Repository Target**: `{report_data.target_path}`  
> **Commit**: `{report_data.commit_info.commit_hash}` (`{report_data.commit_info.branch}`) by *{report_data.commit_info.author}*  
> **Commit Message**: "{report_data.commit_info.message}"  
> **Overall Pipeline Status**: **{status_icon}** | **Overall Quality Score**: `{report_data.quality_score}/100`

---

## 📊 Summary Dashboard

| Metric | Result | Status |
|---|---|---|
| **Static Violations** | `{len(report_data.violations)}` issue(s) | {"✅ Clean" if len(report_data.violations) == 0 else "⚠️ Action Required"} |
| **Unit Tests (pytest)** | `{report_data.test_result.passed}/{report_data.test_result.total_tests}` passed (`{report_data.test_result.coverage_percentage}%` coverage) | {"✅ Passed" if report_data.test_result.success else "❌ Failed"} |
| **AI Code Review** | `{report_data.ai_review.quality_score}/100` score | {"✅ Good" if report_data.ai_review.quality_score >= 80 else "⚠️ Needs Refactoring"} |
| **Docker Build Verification** | {"Passed" if report_data.docker_result.success else "Failed"} | {"✅ Image Built" if report_data.docker_result.success else ("ℹ️ No Dockerfile" if not report_data.docker_result.dockerfile_found else "❌ Build Error")} |

---

## 🔍 Static Analysis & Security (Ruff, Bandit, Semgrep)

"""
    if not report_data.violations:
        md_content += "🎉 *No static analysis or security issues detected!*\n\n"
    else:
        md_content += "| Scanner | File | Line | Rule ID | Severity | Description |\n"
        md_content += "|---|---|---|---|---|---|\n"
        for v in report_data.violations:
            sev_badge = f"**{v.severity.value}**"
            md_content += f"| `{v.scanner_name}` | `{os.path.basename(v.file_path)}` | `{v.line_number}` | `{v.rule_id}` | {sev_badge} | {v.description} |\n"
        md_content += "\n"

    md_content += f"""---

## 🧪 Test Execution & Coverage (pytest)

- **Total Tests Run**: `{report_data.test_result.total_tests}`
- **Passed**: `{report_data.test_result.passed}` | **Failed**: `{report_data.test_result.failed}` | **Skipped**: `{report_data.test_result.skipped}`
- **Execution Duration**: `{report_data.test_result.duration_seconds}s`
- **Code Coverage**: `{report_data.test_result.coverage_percentage}%`

---

## 🤖 AI Code Review & Security Analysis (Ollama)

> **Summary**: {report_data.ai_review.summary}

"""
    if report_data.ai_review.comments:
        md_content += "### Key Review Findings:\n\n"
        for idx, comment in enumerate(report_data.ai_review.comments, 1):
            md_content += f"#### {idx}. [{comment.category}] File: `{comment.file_path}`\n"
            md_content += f"- **Comment**: {comment.comment}\n"
            if comment.suggested_code:
                md_content += f"```python\n{comment.suggested_code}\n```\n"
            md_content += "\n"

    md_content += f"""---

## 🐳 Docker Container Build Validation

- **Dockerfile Found**: `{"Yes" if report_data.docker_result.dockerfile_found else "No"}`
- **Build Status**: `{"Success" if report_data.docker_result.success else "Failure"}`
- **Image Tag**: `{report_data.docker_result.image_tag}`
- **Build Time**: `{report_data.docker_result.duration_seconds}s`

"""
    if report_data.docker_result.failure_reason:
        md_content += f"> ⚠️ **Failure Reason**: `{report_data.docker_result.failure_reason}`\n\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return file_path
