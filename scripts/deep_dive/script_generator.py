"""Generate a deep-dive podcast script for a single research paper."""

import logging

from google import genai

from scripts.config import config
from scripts.deep_dive.paper_fetcher import PaperInfo
from scripts.utils import PODCASTS_DIR, render_template, write_text

logger = logging.getLogger(__name__)

DEEP_DIVE_PROMPT = """\
You are writing a script for "ASR & Speech Language Deep Dive", a two-person podcast episode
that does a thorough technical analysis of a single research paper.

The podcast has two speakers:
- Host: Introduces the paper, asks probing questions, relates the work to
  the broader ASR and speech language model landscape, and ensures accessibility for practitioners.
- Guest: Acts as the domain expert who has read the paper in depth, explains
  methodology, highlights key innovations, discusses limitations, and
  provides practical takeaways.

Format every line of dialogue as:
  Host: <text>
  Guest: <text>

Guidelines:
- Target length: {target_words} words (~10-12 minutes of audio)
- Structure:
  1. Introduction: What is this paper? Who wrote it? Why does it matter?
  2. Problem Statement: What gap or challenge does this paper address?
  3. Methodology Deep-Dive: Walk through the architecture, training procedure,
     and key technical choices. Use analogies to make complex concepts accessible.
  4. Key Results: What did they achieve? How do the numbers compare to prior work?
  5. Practical Implications: How can practitioners use these findings? What models
     are available? How do you get started?
  6. Limitations and Future Work: What are the open questions?
  7. Takeaways: 2-3 bullet-point-style conclusions.
- Make it a natural conversation — speakers should react to each other
- Explain significance to practitioners, not just academics
- Reference specific numbers, model names, and benchmarks from the paper
- End with a forward-looking statement

## Paper Information

Title: {title}
Authors: {authors}
Published: {published}
arXiv: {url}

## Abstract
{abstract}

{content_section}

{hf_section}

{github_section}

Write the full podcast script now (only Host: and Guest: dialogue lines, no stage directions):"""


def generate_deep_dive_script(paper: PaperInfo) -> str:
    """Generate a deep-dive podcast script for a single paper.

    Args:
        paper: PaperInfo dataclass with paper metadata and content.

    Returns:
        The podcast script text.
    """
    # Build optional sections
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

    prompt = DEEP_DIVE_PROMPT.format(
        target_words=config.podcast_target_words,
        title=paper.title,
        authors=", ".join(paper.authors),
        published=paper.published,
        url=paper.url,
        abstract=paper.abstract,
        content_section=content_section,
        hf_section=hf_section,
        github_section=github_section,
    )

    logger.info("Generating deep-dive script with Gemini...")
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
    slug = paper.slug
    content = render_template(
        "deep_dive_script.md.j2",
        title=paper.title,
        arxiv_id=paper.arxiv_id,
        url=paper.url,
        script=script,
    )
    script_path = PODCASTS_DIR / f"{slug}-deep-dive-script.md"
    write_text(script_path, content)
    logger.info("Script written to %s (%d words)", script_path, len(script.split()))

    return script
