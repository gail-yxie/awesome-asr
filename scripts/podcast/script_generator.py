"""Generate a podcast script from today's daily report using Gemini."""

import logging

from google import genai

from scripts.config import config
from scripts.utils import (
    DAILY_DIR,
    PODCASTS_DIR,
    day_tag,
    list_daily_json_reports,
    read_json,
    read_text,
    render_template,
    set_date_override,
    write_text,
)

logger = logging.getLogger(__name__)

PODCAST_PROMPT = """\
You are writing a script for "ASR & Speech Language Daily", a two-person podcast about
Automatic Speech Recognition and Speech Language Model research and developments.

The podcast has two speakers:
- Host: The main presenter who introduces topics and drives the conversation.
- Guest: A knowledgeable co-host who adds insights, asks clarifying questions,
  and provides alternative perspectives.

Format every line of dialogue as:
  Host: <text>
  Guest: <text>

Guidelines:
- Target length: {target_words} words (~10-12 minutes of audio)
- Structure: intro → paper highlights → model releases → trend analysis → outro
- Make it a natural conversation — the speakers should react to each other
- Explain significance to practitioners, not just academics
- Avoid overly academic language; be engaging and accessible
- Reference specific paper titles and model names
- End with a forward-looking statement about where the field is heading

## Today's Report

{reports}

Write the full podcast script now (only Host: and Guest: dialogue lines, no stage directions):"""


def generate_script(date: str | None = None) -> str:
    """Generate a daily podcast script and save it.

    Args:
        date: Specific date (YYYY-MM-DD) to generate for. Defaults to today.

    Returns:
        The podcast script text.
    """
    if date:
        report_path = DAILY_DIR / f"{date}.json"
        reports = [report_path] if report_path.exists() else []
    else:
        reports = list_daily_json_reports(days=1)
    if not reports:
        logger.warning("No daily reports found — cannot generate podcast script")
        return ""

    # Build report summaries
    report_texts = []
    for path in reports:
        data = read_json(path)
        papers_summary = "\n".join(
            f"  - {p['title']} by {', '.join(p['authors'][:2])}"
            for p in data.get("papers", [])[:5]
        )
        models_summary = "\n".join(
            f"  - {m['model_id']} by {m['author']}"
            for m in data.get("models", [])[:3]
        )
        report_texts.append(
            f"### {data.get('date', path.stem)}\n"
            f"Summary: {data.get('summary', 'N/A')}\n"
            f"Key papers:\n{papers_summary}\n"
            f"New models:\n{models_summary}\n"
            f"Ideas: {', '.join(data.get('ideas', []))}"
        )

    reports_text = "\n\n".join(report_texts)
    prompt = PODCAST_PROMPT.format(
        target_words=config.podcast_target_words,
        reports=reports_text,
    )

    logger.info("Generating podcast script with Gemini...")
    client = genai.Client(
        api_key=config.gemini_api_key,
        http_options={"base_url": "https://generativelanguage.googleapis.com"},
    )
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )
    script = response.text.strip()

    # Save script
    dt = day_tag()
    content = render_template("podcast_script.md.j2", date_label=dt, script=script)
    script_path = PODCASTS_DIR / f"{dt}-script.md"
    write_text(script_path, content)
    logger.info("Podcast script written to %s (%d words)", script_path, len(script.split()))

    # Update podcast index
    _update_podcast_index(dt)

    return script


def _update_podcast_index(episode_date: str) -> None:
    """Insert a daily episode row into podcasts/index.md (newest first)."""
    index_path = PODCASTS_DIR / "index.md"
    header = "# ASR & Speech Language Podcast Episodes\n\n| Episode | Date | Audio |\n|---------|------|-------|\n"
    if index_path.exists():
        content = read_text(index_path)
    else:
        content = header

    entry = f"| {episode_date} | {episode_date} | [Listen](/podcasts/audio/{episode_date}.mp3) |"
    if entry in content:
        return

    # Insert after the header row so newest episodes stay at the top
    lines = content.splitlines()
    insert_at = next(
        (i + 1 for i, line in enumerate(lines) if line.startswith("|---")),
        len(lines),
    )
    lines.insert(insert_at, entry)
    write_text(index_path, "\n".join(lines) + "\n")
    logger.info("Updated podcasts/index.md with episode %s", episode_date)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Generate for a specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.date:
        set_date_override(args.date)

    logging.basicConfig(level=logging.INFO)
    generate_script(date=args.date)
