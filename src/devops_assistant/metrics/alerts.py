"""
Alert System for quality regressions.
Sends Slack webhook and/or email notifications when thresholds are breached.
"""

import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from devops_assistant.config import AlertConfig, CIReportData


def _send_slack(webhook_url: str, message: str):
    """Send a message to a Slack webhook."""
    try:
        httpx.post(webhook_url, json={"text": message}, timeout=10.0)
    except Exception as e:
        print(f"[Warning] Slack alert failed: {e}")


def _send_email(config: AlertConfig, subject: str, body: str):
    """Send an email alert via SMTP."""
    if not config.email_to or not config.email_from or not config.smtp_password:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.email_from
        msg["To"] = config.email_to
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
            server.starttls()
            server.login(config.email_from, config.smtp_password)
            server.sendmail(config.email_from, config.email_to, msg.as_string())
    except Exception as e:
        print(f"[Warning] Email alert failed: {e}")


def check_and_alert(report: CIReportData, config: AlertConfig):
    """
    Check report against alert thresholds and fire notifications if breached.
    Always prints a console warning. Optionally sends Slack/email.
    """
    alerts = []

    if report.quality_score < config.min_quality_score:
        alerts.append(
            f"⚠️  Quality score dropped to {report.quality_score}/100 "
            f"(threshold: {config.min_quality_score})"
        )

    if len(report.violations) > config.max_violations:
        alerts.append(
            f"⚠️  {len(report.violations)} violations found "
            f"(threshold: {config.max_violations})"
        )

    if not report.overall_passed:
        alerts.append("❌  CI Pipeline FAILED")

    if not alerts:
        return

    header = f"[AI DevOps Assistant] Alert for run {report.run_id} — {report.target_path}"
    body = "\n".join(alerts)
    full_message = f"{header}\n\n{body}"

    # Always print to console
    print("\n" + "="*60)
    print(full_message)
    print("="*60 + "\n")

    # Slack
    if config.slack_webhook:
        _send_slack(config.slack_webhook, full_message)

    # Email
    if config.email_to:
        _send_email(config, f"[DevOps Alert] {header}", full_message)
