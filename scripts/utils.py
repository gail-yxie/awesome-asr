import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

_retry_logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = PROJECT_ROOT / "daily"
PODCASTS_DIR = PROJECT_ROOT / "podcasts"
MINDMAPS_DIR = PROJECT_ROOT / "mindmaps"
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "templates"


def today_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def day_tag() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def week_tag() -> str:
    now = datetime.utcnow()
    return now.strftime("%Y-W%V")


def read_json(path: Path) -> dict | list:
    with open(path) as f:
        return json.load(f)


def write_json(path: Path, data: dict | list) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def read_text(path: Path) -> str:
    with open(path) as f:
        return f.read()


def daily_report_path(date_str: str, ext: str = "md") -> Path:
    return DAILY_DIR / f"{date_str}.{ext}"


def list_daily_reports(days: int = 7) -> list[Path]:
    """Return paths to the most recent daily report markdown files."""
    reports = sorted(DAILY_DIR.glob("????-??-??.md"), reverse=True)
    return reports[:days]


def list_daily_json_reports(days: int = 7) -> list[Path]:
    """Return paths to the most recent daily report JSON files."""
    reports = sorted(DAILY_DIR.glob("????-??-??.json"), reverse=True)
    return reports[:days]


def retry(fn, max_retries: int = 3, base_delay: float = 5.0):
    """Call fn() with exponential backoff retry on transient errors."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            err_str = str(e).lower()
            is_transient = any(
                kw in err_str
                for kw in ("429", "503", "overloaded", "high demand", "resource exhausted", "rate limit")
            )
            if not is_transient or attempt >= max_retries:
                raise
            delay = base_delay * (2 ** attempt)
            _retry_logger.warning(
                "Transient error (attempt %d/%d), retrying in %.0fs: %s",
                attempt + 1, max_retries, delay, e,
            )
            time.sleep(delay)


def render_template(template_name: str, **context) -> str:
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(template_name)
    return template.render(**context)
