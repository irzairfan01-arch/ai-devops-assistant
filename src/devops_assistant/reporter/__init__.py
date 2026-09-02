"""
CI Report Generators
"""

from devops_assistant.reporter.markdown_report import generate_markdown_report
from devops_assistant.reporter.html_report import generate_html_report

__all__ = ["generate_markdown_report", "generate_html_report"]
