"""Generate a paper-specific mindmap showing the paper's structure and contributions."""

import json
import logging
from pathlib import Path

from google import genai

from scripts.config import config
from scripts.deep_dive.paper_fetcher import PaperInfo
from scripts.utils import MINDMAPS_DIR, write_text

logger = logging.getLogger(__name__)

PAPER_MINDMAP_PROMPT = """\
You are an expert in Automatic Speech Recognition (ASR) research.

Given a research paper's information, create a hierarchical mindmap structure
that captures the paper's architecture, contributions, and methodology.

The mindmap should have the paper title as the root, with these top-level sections:
1. Problem & Motivation
2. Architecture / Method (with sub-components)
3. Training (data, procedure, losses)
4. Key Results (benchmarks, comparisons)
5. Contributions (what's novel)
6. Available Resources (models, code, datasets)

Make the structure detailed enough to serve as a study guide for someone
learning about this paper. Include specific numbers, model names, and
technical details from the paper.

## Paper Information

Title: {title}
Authors: {authors}

## Abstract
{abstract}

{content_section}

{hf_section}

{github_section}

Return ONLY valid JSON, no explanation. The JSON should be a nested dict
where keys are section/subsection names and values are either nested dicts
or lists of strings for leaf items. Example:
{{
  "Paper Title": {{
    "Problem & Motivation": ["point 1", "point 2"],
    "Architecture": {{
      "Encoder": ["detail 1", "detail 2"],
      "Decoder": ["detail 1"]
    }}
  }}
}}"""


def _taxonomy_to_markdown(taxonomy: dict, level: int = 1) -> str:
    """Convert a nested dict to markdown headings for markmap rendering."""
    lines = []
    for key, value in taxonomy.items():
        prefix = "#" * level
        lines.append(f"{prefix} {key}")
        if isinstance(value, dict):
            lines.append(_taxonomy_to_markdown(value, level + 1))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines)


def generate_paper_mindmap(paper: PaperInfo) -> Path | None:
    """Generate a mindmap markdown file for a single paper.

    Args:
        paper: PaperInfo dataclass with paper metadata and content.

    Returns:
        Path to the generated markdown file, or None on failure.
    """
    content_section = ""
    if paper.full_text:
        content_section = f"## Paper Content\n{paper.full_text}"

    hf_section = ""
    if paper.hf_models:
        models_list = "\n".join(f"- https://huggingface.co/{m}" for m in paper.hf_models)
        hf_section = f"## Available HuggingFace Models\n{models_list}"

    github_section = ""
    if paper.github_url:
        github_section = f"## GitHub Repository\n{paper.github_url}"

    prompt = PAPER_MINDMAP_PROMPT.format(
        title=paper.title,
        authors=", ".join(paper.authors),
        abstract=paper.abstract,
        content_section=content_section,
        hf_section=hf_section,
        github_section=github_section,
    )

    logger.info("Generating paper mindmap with Gemini...")
    client = genai.Client(
        api_key=config.gemini_api_key,
        http_options={"base_url": "https://generativelanguage.googleapis.com"},
    )
    response = client.models.generate_content(
        model=config.gemini_model,
        contents=prompt,
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        taxonomy = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse mindmap JSON from Gemini response")
        return None

    md_content = _taxonomy_to_markdown(taxonomy)
    md_path = MINDMAPS_DIR / f"{paper.slug}-deep-dive.md"
    write_text(md_path, md_content)
    logger.info("Mindmap markdown written to %s", md_path)
    return md_path
