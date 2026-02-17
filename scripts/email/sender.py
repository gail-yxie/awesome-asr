"""Send daily ASR update emails to subscribers via self-hosted SMTP."""

import csv
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.config import config
from scripts.utils import DATA_DIR, daily_report_path, read_json, today_str

logger = logging.getLogger(__name__)

SUBSCRIBERS_PATH = DATA_DIR / "subscribers.csv"
EMAIL_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_subscribers() -> list[dict]:
    """Load subscriber list from CSV."""
    if not SUBSCRIBERS_PATH.exists():
        logger.warning("Subscribers file not found: %s", SUBSCRIBERS_PATH)
        return []

    subscribers = []
    with open(SUBSCRIBERS_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("email"):
                subscribers.append(row)

    logger.info("Loaded %d subscribers", len(subscribers))
    return subscribers


def _render_email(report: dict) -> str:
    """Render the HTML email from template."""
    env = Environment(loader=FileSystemLoader(str(EMAIL_TEMPLATES_DIR)))
    template = env.get_template("daily_email.html")
    return template.render(
        report=report,
        site_url=config.site_url,
    )


def _send_email(to_email: str, to_name: str, subject: str, html_body: str) -> bool:
    """Send a single email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.smtp_from_address
    msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email

    msg.attach(MIMEText(html_body, "html"))

    try:
        if config.smtp_use_tls:
            server = smtplib.SMTP(config.smtp_host, config.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(config.smtp_host, config.smtp_port)

        if config.smtp_user and config.smtp_password:
            server.login(config.smtp_user, config.smtp_password)

        server.sendmail(config.smtp_from_address, to_email, msg.as_string())
        server.quit()
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_daily_email() -> None:
    """Send today's daily report to all subscribers."""
    if not config.email_enabled:
        logger.info("Email not configured — skipping")
        return

    date = today_str()
    json_path = daily_report_path(date, "json")
    if not json_path.exists():
        logger.warning("No daily report found for %s", date)
        return

    report = read_json(json_path)
    subscribers = _load_subscribers()
    if not subscribers:
        logger.info("No subscribers — skipping email")
        return

    html_body = _render_email(report)
    subject = f"ASR Daily Update — {date}"

    sent = 0
    failed = 0
    for sub in subscribers:
        if _send_email(sub["email"], sub.get("name", ""), subject, html_body):
            sent += 1
        else:
            failed += 1

    logger.info("Emails sent: %d, failed: %d", sent, failed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    send_daily_email()
