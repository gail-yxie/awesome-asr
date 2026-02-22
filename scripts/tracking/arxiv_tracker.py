"""Fetch recent ASR and speech language model papers from the arXiv API."""

import logging
import time
from datetime import datetime, timedelta

import feedparser
import requests

from scripts.config import config
from scripts.utils import DATA_DIR, read_json

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds


def _build_query() -> str:
    """Build an arXiv search query from configured search terms and categories."""
    queries = read_json(DATA_DIR / "search_queries.json")
    terms = queries["arxiv_queries"]
    categories = queries["arxiv_categories"]

    term_query = " OR ".join(f'all:"{t}"' for t in terms)
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    return f"({term_query}) AND ({cat_query})"


def fetch_papers(lookback_hours: int = 48, max_results: int = 100) -> list[dict]:
    """Fetch recent ASR and speech language model papers from arXiv.

    Args:
        lookback_hours: How far back to search (arXiv updates can be delayed).
        max_results: Maximum number of results to return.

    Returns:
        List of paper dicts with keys: id, title, authors, abstract,
        categories, published, url, pdf_url.
    """
    query = _build_query()
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    logger.info("Querying arXiv API...")
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.get(ARXIV_API_URL, params=params, timeout=60)
        if resp.status_code == 429:
            delay = RETRY_DELAY * attempt
            logger.warning("arXiv rate limit hit (attempt %d/%d), retrying in %ds...", attempt, MAX_RETRIES, delay)
            time.sleep(delay)
            continue
        resp.raise_for_status()
        break
    else:
        logger.error("arXiv API rate limit exceeded after %d retries", MAX_RETRIES)
        return []

    feed = feedparser.parse(resp.text)
    cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)

    papers = []
    for entry in feed.entries:
        published = datetime(*entry.published_parsed[:6])
        if published < cutoff:
            continue

        arxiv_id = entry.id.split("/abs/")[-1]
        papers.append(
            {
                "id": arxiv_id,
                "title": entry.title.replace("\n", " ").strip(),
                "authors": [a.name for a in entry.authors],
                "abstract": entry.summary.replace("\n", " ").strip(),
                "categories": [t.term for t in entry.tags],
                "published": published.strftime("%Y-%m-%d"),
                "url": entry.link,
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
            }
        )

    logger.info("Found %d recent ASR/speech language papers on arXiv", len(papers))
    return papers


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    results = fetch_papers()
    print(json.dumps(results, indent=2))
