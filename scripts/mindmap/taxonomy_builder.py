"""Build and update the ASR topic taxonomy, then generate mindmap markdown files."""

import json
import logging

from google import genai

from scripts.config import config
from scripts.utils import (
    DATA_DIR,
    MINDMAPS_DIR,
    list_daily_json_reports,
    read_json,
    write_json,
    write_text,
)

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = """\
You are an expert in Automatic Speech Recognition (ASR) research.

Given the existing ASR topic taxonomy and a list of recent papers and models,
classify each item into the taxonomy. If an item doesn't fit any existing category,
suggest a new leaf node (but avoid creating new top-level categories).

## Current Taxonomy
{taxonomy}

## Recent Papers and Models
{items}

Return the updated taxonomy as JSON. Keep the same structure but add new leaf nodes
where appropriate. Only add items that are genuinely new and significant.
Return ONLY valid JSON, no explanation:"""


def _taxonomy_to_markdown(taxonomy: dict, level: int = 1) -> str:
    """Convert a nested dict taxonomy to markdown headings."""
    lines = []
    for key, value in taxonomy.items():
        prefix = "#" * level
        lines.append(f"{prefix} {key}")
        if isinstance(value, dict):
            lines.append(_taxonomy_to_markdown(value, level + 1))
        elif isinstance(value, list):
            for item in value:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def _collect_recent_items() -> str:
    """Collect recent papers and models from daily reports."""
    reports = list_daily_json_reports(days=config.mindmap_lookback_days)
    items = []
    for path in reports:
        data = read_json(path)
        for p in data.get("papers", [])[:5]:
            items.append(f"Paper: {p['title']}")
        for m in data.get("models", [])[:3]:
            items.append(f"Model: {m['model_id']}")

    return "\n".join(items) if items else "No recent items found."


def update_taxonomy() -> dict:
    """Update the taxonomy with recent papers/models using Gemini."""
    taxonomy_path = DATA_DIR / "topic_taxonomy.json"
    taxonomy = read_json(taxonomy_path)
    recent_items = _collect_recent_items()

    if recent_items == "No recent items found.":
        logger.info("No recent items — taxonomy unchanged")
        return taxonomy

    prompt = CLASSIFY_PROMPT.format(
        taxonomy=json.dumps(taxonomy, indent=2),
        items=recent_items,
    )

    logger.info("Updating taxonomy with Gemini...")
    client = genai.Client(api_key=config.gemini_api_key)
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        updated = json.loads(text)
        write_json(taxonomy_path, updated)
        logger.info("Taxonomy updated")
        return updated
    except json.JSONDecodeError:
        logger.error("Failed to parse updated taxonomy — keeping original")
        return taxonomy


def generate_mindmap_markdown() -> None:
    """Generate markdown files for mindmap rendering."""
    taxonomy = update_taxonomy()

    # 1. ASR Overview mindmap
    overview_md = _taxonomy_to_markdown(taxonomy)
    write_text(MINDMAPS_DIR / "asr-overview.md", overview_md)
    logger.info("Generated asr-overview.md")

    # 2. Recent Papers mindmap (organized by topic)
    reports = list_daily_json_reports(days=config.mindmap_lookback_days)
    papers_by_cat = {}
    for path in reports:
        data = read_json(path)
        for p in data.get("papers", []):
            cat = p.get("categories", ["Uncategorized"])[0]
            papers_by_cat.setdefault(cat, []).append(p["title"])

    if papers_by_cat:
        lines = ["# Recent ASR Papers", ""]
        for cat, titles in sorted(papers_by_cat.items()):
            lines.append(f"## {cat}")
            for t in titles[:10]:
                lines.append(f"- {t}")
            lines.append("")
        write_text(MINDMAPS_DIR / "recent-papers.md", "\n".join(lines))
        logger.info("Generated recent-papers.md")

    # 3. Models mindmap
    all_models = []
    for path in reports:
        data = read_json(path)
        all_models.extend(data.get("models", []))

    if all_models:
        models_by_author = {}
        for m in all_models:
            models_by_author.setdefault(m["author"], []).append(m["model_id"])

        lines = ["# ASR Models", ""]
        for author, model_ids in sorted(models_by_author.items()):
            lines.append(f"## {author}")
            for mid in model_ids[:10]:
                lines.append(f"- {mid}")
            lines.append("")
        write_text(MINDMAPS_DIR / "models.md", "\n".join(lines))
        logger.info("Generated models.md")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_mindmap_markdown()
