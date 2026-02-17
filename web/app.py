"""Flask web application for displaying ASR daily trends, podcasts, and mindmaps."""

import json
from pathlib import Path

import markdown
from flask import Flask, abort, render_template, send_from_directory

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = PROJECT_ROOT / "daily"
DATA_DIR = PROJECT_ROOT / "data"
PODCASTS_DIR = PROJECT_ROOT / "podcasts"
MINDMAPS_DIR = PROJECT_ROOT / "mindmaps"


def _load_daily_reports(limit: int = 30) -> list[dict]:
    """Load daily JSON reports, most recent first."""
    reports = []
    for path in sorted(DAILY_DIR.glob("????-??-??.json"), reverse=True)[:limit]:
        with open(path) as f:
            reports.append(json.load(f))
    return reports


def _load_daily_report(date: str) -> dict | None:
    """Load a single daily report by date string."""
    path = DAILY_DIR / f"{date}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _load_podcast_index() -> list[dict]:
    """Parse podcasts/index.md to get episode list."""
    index_path = PODCASTS_DIR / "index.md"
    if not index_path.exists():
        return []

    episodes = []
    for line in index_path.read_text().splitlines():
        if line.startswith("|") and not line.startswith("| Episode") and "---" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 3:
                # Extract URL from markdown link
                audio_link = parts[2]
                url = ""
                if "(" in audio_link:
                    url = audio_link.split("(")[1].rstrip(")")
                episodes.append(
                    {
                        "episode": parts[0],
                        "date": parts[1],
                        "audio_url": url,
                    }
                )
    return episodes


@app.route("/")
def index():
    """Dashboard: today's summary, recent highlights, latest podcast."""
    reports = _load_daily_reports(limit=7)
    latest = reports[0] if reports else None
    podcasts = _load_podcast_index()
    latest_podcast = podcasts[0] if podcasts else None

    return render_template(
        "index.html",
        latest_report=latest,
        recent_reports=reports[:5],
        latest_podcast=latest_podcast,
    )


@app.route("/daily")
def daily_list():
    """Paginated list of all daily reports."""
    reports = _load_daily_reports(limit=100)
    return render_template("daily_list.html", reports=reports)


@app.route("/daily/<date>")
def daily_detail(date: str):
    """Single daily report view."""
    report = _load_daily_report(date)
    if report is None:
        abort(404)

    # Also try to load the markdown version for rich rendering
    md_path = DAILY_DIR / f"{date}.md"
    html_content = ""
    if md_path.exists():
        html_content = markdown.markdown(
            md_path.read_text(),
            extensions=["tables", "fenced_code"],
        )

    return render_template(
        "daily.html",
        report=report,
        html_content=html_content,
    )


@app.route("/podcasts")
def podcasts():
    """Podcast episodes listing."""
    episodes = _load_podcast_index()

    # Also list script files
    scripts = sorted(PODCASTS_DIR.glob("*-script.md"), reverse=True)
    script_map = {}
    for s in scripts:
        key = s.stem.replace("-script", "")
        script_map[key] = markdown.markdown(s.read_text())

    return render_template(
        "podcasts.html",
        episodes=episodes,
        script_map=script_map,
    )


@app.route("/models")
def models():
    """Open-source ASR models catalog."""
    models_path = DATA_DIR / "models.json"
    model_list = []
    if models_path.exists():
        with open(models_path) as f:
            model_list = json.load(f)
    return render_template("models.html", models=model_list)


@app.route("/mindmaps")
def mindmaps():
    """Mindmap viewer."""
    html_files = sorted(MINDMAPS_DIR.glob("*.html"))
    maps = [{"name": f.stem, "filename": f.name} for f in html_files]
    return render_template("mindmaps.html", maps=maps)


@app.route("/mindmaps/<filename>")
def serve_mindmap(filename: str):
    """Serve a mindmap HTML file."""
    return send_from_directory(str(MINDMAPS_DIR), filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
