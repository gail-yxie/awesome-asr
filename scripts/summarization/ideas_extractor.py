"""Weekly ideas summary: aggregates daily ideas into a consolidated report."""

import json
import logging
from datetime import datetime

from google import genai

from scripts.config import config
from scripts.utils import (
    DAILY_DIR,
    list_daily_json_reports,
    read_json,
    render_template,
    week_tag,
    write_text,
)

logger = logging.getLogger(__name__)

WEEKLY_SUMMARY_PROMPT = """\
You are an expert in Automatic Speech Recognition (ASR) research.
Given the past week's daily ASR updates, produce a structured weekly ideas summary.

For each section, provide 2-5 bullet points. Be specific and cite paper titles where relevant.

Sections:
1. **Breakthroughs**: Major new results or capabilities
2. **Emerging Trends**: Patterns you see across multiple papers/releases
3. **Notable Techniques**: New methods or approaches worth watching
4. **Connections**: How different papers/models relate to each other

## This Week's Daily Reports
{reports}

Return your response as JSON with keys: breakthroughs, trends, techniques, connections.
Each key maps to a list of strings. Example:
{{"breakthroughs": ["Point 1", "Point 2"], "trends": [...], "techniques": [...], "connections": [...]}}"""


def generate_weekly_summary() -> None:
    """Generate a weekly ideas summary from the past 7 days of daily reports."""
    reports = list_daily_json_reports(days=7)
    if not reports:
        logger.info("No daily reports found — skipping weekly summary")
        return

    # Collect all report data
    all_data = []
    for path in reports:
        data = read_json(path)
        all_data.append(
            f"### {data.get('date', path.stem)}\n"
            f"Papers: {len(data.get('papers', []))}, "
            f"Models: {len(data.get('models', []))}\n"
            f"Summary: {data.get('summary', 'N/A')}\n"
            f"Ideas: {', '.join(data.get('ideas', []))}"
        )

    reports_text = "\n\n".join(all_data)
    prompt = WEEKLY_SUMMARY_PROMPT.format(reports=reports_text)

    client = genai.Client(api_key=config.gemini_api_key)
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )

    # Parse JSON response
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON: %s", text[:200])
        data = {
            "breakthroughs": ["Unable to parse weekly summary."],
            "trends": [],
            "techniques": [],
            "connections": [],
        }

    wt = week_tag()
    content = render_template(
        "ideas_summary.md.j2",
        week_label=wt,
        breakthroughs=data.get("breakthroughs", []),
        trends=data.get("trends", []),
        techniques=data.get("techniques", []),
        connections=data.get("connections", []),
    )

    output_path = DAILY_DIR / f"ideas-summary-{wt}.md"
    write_text(output_path, content)
    logger.info("Weekly ideas summary written to %s", output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_weekly_summary()
