"""Generate a podcast script from the week's daily reports using Gemini."""

import logging

from google import genai

from scripts.config import config
from scripts.utils import (
    PODCASTS_DIR,
    list_daily_json_reports,
    read_json,
    render_template,
    week_tag,
    write_text,
)

logger = logging.getLogger(__name__)

PODCAST_PROMPT = """\
You are a professional podcast host for "ASR Weekly", a podcast about
Automatic Speech Recognition research and developments.

Write a podcast script summarizing this week's ASR developments. The script
should be conversational but informative, suitable for spoken delivery.

Guidelines:
- Target length: {target_words} words (~10-12 minutes of audio)
- Structure: intro → paper highlights → model releases → trend analysis → outro
- Explain significance to practitioners, not just academics
- Use smooth transitions between topics
- Avoid overly academic language; be engaging and accessible
- Reference specific paper titles and model names
- End with a forward-looking statement about where the field is heading

## This Week's Daily Reports

{reports}

Write the full podcast script now (just the spoken text, no stage directions):"""


def generate_script() -> str:
    """Generate a weekly podcast script and save it.

    Returns:
        The podcast script text.
    """
    reports = list_daily_json_reports(days=7)
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
    client = genai.Client(api_key=config.gemini_api_key)
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )
    script = response.text.strip()

    # Save script
    wt = week_tag()
    content = render_template("podcast_script.md.j2", week_label=wt, script=script)
    script_path = PODCASTS_DIR / f"{wt}-script.md"
    write_text(script_path, content)
    logger.info("Podcast script written to %s (%d words)", script_path, len(script.split()))

    return script


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_script()
