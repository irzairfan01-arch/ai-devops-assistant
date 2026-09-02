"""
HTML CI Dashboard Report Generator.
"""

import os
from jinja2 import Template
from devops_assistant.config import CIReportData

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI DevOps Assistant — CI Report</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 0.5rem 1rem;
            line-height: 1.3;
            font-size: 0.85rem;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
            margin-bottom: 0.5rem;
        }

        .header h1 {
            margin: 0;
            font-size: 1.2rem;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header p {
            font-size: 0.8rem;
        }

        .badge {
            padding: 0.15rem 0.4rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.7rem;
            display: inline-block;
        }

        .badge-pass { background-color: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }
        .badge-fail { background-color: rgba(239, 68, 68, 0.2); color: var(--accent-red); border: 1px solid var(--accent-red); }
        .badge-warn { background-color: rgba(245, 158, 11, 0.2); color: var(--accent-amber); border: 1px solid var(--accent-amber); }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.5rem;
            margin-bottom: 1rem;
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.3);
        }

        .card h3 {
            margin: 0 0 0.2rem 0;
            color: var(--text-muted);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card .metric {
            font-size: 1.4rem;
            font-weight: 700;
            margin: 0;
        }

        .card small {
            font-size: 0.7rem;
        }

        .section-title {
            font-size: 1rem;
            border-left: 3px solid var(--accent-blue);
            padding-left: 0.5rem;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background-color: var(--card-bg);
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }

        th, td {
            padding: 0.3rem 0.5rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.8rem;
        }

        th {
            background-color: rgba(255, 255, 255, 0.05);
            color: var(--text-muted);
            font-size: 0.75rem;
            text-transform: uppercase;
        }

        code {
            font-family: 'Fira Code', monospace;
            background: rgba(255,255,255,0.1);
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.85em;
        }

        pre {
            background: #090d16;
            padding: 0.5rem;
            margin: 0.5rem 0;
            border-radius: 6px;
            overflow-x: auto;
            color: #e2e8f0;
            border: 1px solid var(--border-color);
            font-size: 0.8rem;
        }

        a.file-link {
            color: var(--accent-blue);
            text-decoration: none;
            font-weight: 600;
        }
        a.file-link:hover {
            text-decoration: underline;
        }

        .review-card {
            margin-bottom: 0.5rem;
        }
        .review-card p {
            margin: 0.2rem 0;
        }
        .review-comment {
            border-top: 1px solid var(--border-color);
            padding-top: 0.5rem;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🤖 AI DevOps Assistant — CI Report</h1>
                <p style="color: var(--text-muted); margin: 0.2rem 0 0 0;">Target: <code>{{ report.target_path }}</code> | Commit: <code>{{ report.commit_info.commit_hash }}</code> ({{ report.commit_info.branch }})</p>
            </div>
            <div>
                {% if report.overall_passed %}
                <span class="badge badge-pass">PASSED</span>
                {% else %}
                <span class="badge badge-fail">FAILED</span>
                {% endif %}
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Overall Quality</h3>
                <div class="metric" style="color: var(--accent-blue);">{{ report.quality_score }}/100</div>
                <small style="color: var(--text-muted);">From linters, tests & AI</small>
            </div>
            <div class="card">
                <h3>Static Violations</h3>
                <div class="metric" style="color: {{ 'var(--accent-green)' if report.violations|length == 0 else 'var(--accent-amber)' }};">{{ report.violations|length }}</div>
                <small style="color: var(--text-muted);">Ruff, Bandit & Semgrep</small>
            </div>
            <div class="card">
                <h3>Test Pass Rate</h3>
                <div class="metric" style="color: {{ 'var(--accent-green)' if report.test_result.success else 'var(--accent-red)' }};">
                    {{ report.test_result.passed }}/{{ report.test_result.total_tests }}
                </div>
                <small style="color: var(--text-muted);">coverage: {{ report.test_result.coverage_percentage }}%</small>
            </div>
            <div class="card">
                <h3>Docker Build</h3>
                <div class="metric" style="color: {{ 'var(--accent-green)' if report.docker_result.success else 'var(--accent-red)' }};">
                    {{ "Passed" if report.docker_result.success else "Failed" }}
                </div>
                <small style="color: var(--text-muted);">{{ report.docker_result.image_tag }}</small>
            </div>
        </div>

        <h2 class="section-title">Static Analysis & Vulnerabilities</h2>
        {% if report.violations %}
        <table>
            <thead>
                <tr>
                    <th>Scanner</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Rule ID</th>
                    <th>Severity</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                {% for v in report.violations %}
                <tr>
                    <td><code>{{ v.scanner_name }}</code></td>
                    <td><a href="file:///{{ v.file_path }}#L{{ v.line_number }}" class="file-link" target="_blank">{{ v.file_path }}</a></td>
                    <td>{{ v.line_number }}</td>
                    <td><code>{{ v.rule_id }}</code></td>
                    <td>
                        <span class="badge {{ 'badge-fail' if 'HIGH' in str(v.severity) or 'CRITICAL' in str(v.severity) else 'badge-warn' }}">
                            {{ str(v.severity).replace('Severity.', '') }}
                        </span>
                    </td>
                    <td>{{ v.description }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p style="color: var(--accent-green); margin: 0.5rem 0;">🎉 No static violations detected!</p>
        {% endif %}

        <h2 class="section-title">AI Automated Code Review</h2>
        <div class="card review-card">
            <p><strong>Review Summary:</strong> {{ report.ai_review.summary }}</p>
            {% for comment in report.ai_review.comments %}
            <div class="review-comment">
                <span class="badge badge-warn">{{ comment.category }}</span>
                <strong><a href="file:///{{ report.target_path }}/{{ comment.file_path }}{{ '#L' + str(comment.line_number) if comment.line_number else '' }}" class="file-link" target="_blank">{{ comment.file_path }}</a></strong> (Line {{ comment.line_number or 'N/A' }})
                <p>{{ comment.comment }}</p>
                {% if comment.suggested_code %}
                <pre><code>{{ comment.suggested_code }}</code></pre>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""


def generate_html_report(report_data: CIReportData, output_dir: str = "ci_reports") -> str:
    """Renders CI report into HTML dashboard file."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "ci_report.html")

    template = Template(HTML_TEMPLATE)
    html_out = template.render(report=report_data, str=str)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_out)

    return file_path
