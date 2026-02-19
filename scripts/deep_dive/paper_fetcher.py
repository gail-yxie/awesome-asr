"""Fetch paper metadata and content from arXiv."""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import feedparser
import requests

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"


@dataclass
class PaperInfo:
    """Structured paper metadata and content."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: str
    url: str
    pdf_url: str
    slug: str
    full_text: str | None = None
    hf_models: list[str] = field(default_factory=list)
    github_url: str | None = None


def parse_arxiv_input(input_str: str) -> str:
    """Extract arXiv ID from various input formats.

    Accepts:
      - "2601.21337"
      - "2601.21337v1"
      - "https://arxiv.org/abs/2601.21337"
      - "https://arxiv.org/pdf/2601.21337"
    """
    input_str = input_str.strip()
    # Strip arXiv URL prefix
    for prefix in ("https://arxiv.org/abs/", "https://arxiv.org/pdf/", "http://arxiv.org/abs/"):
        if input_str.startswith(prefix):
            input_str = input_str[len(prefix):]
            break
    # Remove trailing version and .pdf
    input_str = input_str.rstrip("/").removesuffix(".pdf")
    return input_str


def _generate_slug(title: str) -> str:
    """Generate a URL-safe slug from a paper title."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug).strip("-")
    return slug[:60].rstrip("-")


def fetch_paper(arxiv_id: str) -> PaperInfo:
    """Fetch paper metadata from the arXiv API."""
    params = {"id_list": arxiv_id, "max_results": 1}
    logger.info("Fetching arXiv metadata for %s...", arxiv_id)

    resp = requests.get(ARXIV_API_URL, params=params, timeout=30)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    if not feed.entries:
        raise ValueError(f"No paper found for arXiv ID: {arxiv_id}")

    entry = feed.entries[0]
    published = datetime(*entry.published_parsed[:6])
    entry_id = entry.id.split("/abs/")[-1]

    title = entry.title.replace("\n", " ").strip()
    paper = PaperInfo(
        arxiv_id=entry_id,
        title=title,
        authors=[a.name for a in entry.authors],
        abstract=entry.summary.replace("\n", " ").strip(),
        categories=[t.term for t in entry.tags],
        published=published.strftime("%Y-%m-%d"),
        url=entry.link,
        pdf_url=f"https://arxiv.org/pdf/{entry_id}",
        slug=_generate_slug(title),
    )
    logger.info("Fetched: %s", paper.title)
    return paper


def fetch_full_text(arxiv_id: str) -> str | None:
    """Attempt to fetch full paper text from arXiv HTML version."""
    # Strip version suffix for HTML URL
    base_id = re.sub(r"v\d+$", "", arxiv_id)
    html_url = f"https://arxiv.org/html/{base_id}"
    logger.info("Attempting full text fetch from %s", html_url)

    try:
        resp = requests.get(html_url, timeout=30)
        if resp.status_code != 200:
            logger.info("HTML version not available (status %d)", resp.status_code)
            return None

        # Extract article body text — strip HTML tags
        text = resp.text
        # Find the article content
        match = re.search(r"<article[^>]*>(.*?)</article>", text, re.DOTALL)
        if match:
            text = match.group(1)

        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) < 500:
            logger.info("Extracted text too short (%d chars), skipping", len(text))
            return None

        # Truncate to reasonable length for Gemini context
        if len(text) > 50000:
            text = text[:50000] + "..."

        logger.info("Extracted %d chars of full text", len(text))
        return text

    except requests.RequestException as e:
        logger.info("Failed to fetch HTML version: %s", e)
        return None


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    paper = fetch_paper("2601.21337")
    paper.full_text = fetch_full_text(paper.arxiv_id)
    print(json.dumps({
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": paper.authors[:5],
        "slug": paper.slug,
        "full_text_chars": len(paper.full_text) if paper.full_text else 0,
    }, indent=2))
