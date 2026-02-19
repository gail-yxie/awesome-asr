"""Batch-generate podcasts and mindmaps for all models in the catalog.

Iterates over data/models.json, deduplicates by arXiv paper ID, and runs
the deep-dive pipeline for each paper not yet in data/model_media.json.

Usage:
    python -m scripts.generate_model_media
    python -m scripts.generate_model_media --no-audio      # mindmaps only
    python -m scripts.generate_model_media --no-mindmap     # podcasts only
    python -m scripts.generate_model_media --force          # regenerate all
"""

import argparse
import logging
from datetime import datetime

from scripts.deep_dive.pipeline import run_pipeline
from scripts.utils import DATA_DIR, read_json, write_json

logger = logging.getLogger(__name__)

MEDIA_PATH = DATA_DIR / "model_media.json"


def _extract_arxiv_id(paper_url: str) -> str | None:
    if not paper_url:
        return None
    for prefix in (
        "https://arxiv.org/abs/",
        "https://arxiv.org/pdf/",
        "http://arxiv.org/abs/",
    ):
        if paper_url.startswith(prefix):
            return paper_url[len(prefix) :].rstrip("/")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate podcasts/mindmaps for all catalog models."
    )
    parser.add_argument(
        "--no-audio", action="store_true", help="Skip podcast audio generation"
    )
    parser.add_argument(
        "--no-mindmap", action="store_true", help="Skip mindmap generation"
    )
    parser.add_argument(
        "--force", action="store_true", help="Regenerate even if already exists"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    models = read_json(DATA_DIR / "models.json")

    media = {}
    if MEDIA_PATH.exists():
        media = read_json(MEDIA_PATH)

    # Deduplicate by arXiv ID
    papers_to_process = {}
    for m in models:
        arxiv_id = _extract_arxiv_id(m.get("paper_url", ""))
        if arxiv_id and (args.force or arxiv_id not in media):
            papers_to_process[arxiv_id] = m.get("paper_url", "")

    logger.info("Found %d unique papers to process", len(papers_to_process))

    for arxiv_id, paper_url in papers_to_process.items():
        logger.info("Processing arXiv %s ...", arxiv_id)
        try:
            result = run_pipeline(
                arxiv_input=arxiv_id,
                skip_audio=args.no_audio,
                skip_mindmap=args.no_mindmap,
            )
            paper = result["paper"]
            entry = {
                "slug": paper.slug,
                "generated_at": datetime.utcnow().isoformat(),
            }
            if result.get("audio_path"):
                entry["podcast_audio"] = result["audio_path"].name
                entry["podcast_script"] = f"{paper.slug}-deep-dive-script.md"
            if result.get("mindmap_html_path"):
                entry["mindmap_html"] = result["mindmap_html_path"].name
                entry["mindmap_md"] = f"{paper.slug}-deep-dive.md"

            media[arxiv_id] = entry
            write_json(MEDIA_PATH, media)
            logger.info("Completed: %s", paper.title)

        except Exception:
            logger.exception("Failed to process arXiv %s", arxiv_id)

    logger.info("Done. %d papers in media index.", len(media))


if __name__ == "__main__":
    main()
