"""Daily aggregator: fetches from all sources, summarizes, and writes reports."""

import logging
from datetime import datetime

from scripts.summarization.summarizer import extract_ideas, summarize_daily
from scripts.tracking.arxiv_tracker import fetch_papers
from scripts.tracking.huggingface_tracker import fetch_datasets, fetch_models
from scripts.tracking.leaderboard_tracker import update_leaderboard
from scripts.tracking.twitter_tracker import fetch_tweets
from scripts.utils import (
    daily_report_path,
    render_template,
    today_str,
    write_json,
    write_text,
)

logger = logging.getLogger(__name__)


def _deduplicate_papers(papers: list[dict]) -> list[dict]:
    """Remove duplicate papers based on arXiv ID or title similarity."""
    seen_ids = set()
    seen_titles = set()
    unique = []
    for p in papers:
        pid = p.get("id", "")
        title_key = p["title"].lower().strip()
        if pid in seen_ids or title_key in seen_titles:
            continue
        seen_ids.add(pid)
        seen_titles.add(title_key)
        unique.append(p)
    return unique


def run_daily_aggregation() -> dict:
    """Run the full daily tracking and aggregation pipeline.

    Returns:
        The aggregated report data dict.
    """
    date = today_str()
    logger.info("Starting daily aggregation for %s", date)

    # Fetch from all sources
    papers = fetch_papers()
    models = fetch_models()
    datasets = fetch_datasets()
    tweets = fetch_tweets()

    # Deduplicate
    papers = _deduplicate_papers(papers)

    # Update leaderboard
    logger.info("Updating Open ASR Leaderboard...")
    leaderboard_top, newly_promoted = update_leaderboard()

    # Summarize with LLM
    logger.info("Generating daily summary...")
    summary = summarize_daily(papers, models, tweets)
    ideas = extract_ideas(papers)

    # Add notes about newly promoted leaderboard models
    for m in newly_promoted:
        ideas.append(
            f"New model on Open ASR Leaderboard top 10: {m['model_id']} "
            f"(avg WER: {m['avg_wer']}%)"
        )

    # Build report data
    report_data = {
        "date": date,
        "summary": summary,
        "ideas": ideas,
        "papers": papers,
        "models": models,
        "datasets": datasets,
        "tweets": tweets,
        "stats": {
            "paper_count": len(papers),
            "model_count": len(models),
            "dataset_count": len(datasets),
            "tweet_count": len(tweets),
        },
    }

    # Write JSON (for website and email)
    json_path = daily_report_path(date, "json")
    write_json(json_path, report_data)
    logger.info("Daily JSON report written to %s", json_path)

    # Write markdown (for GitHub and humans)
    md_content = render_template(
        "daily_report.md.j2",
        date=date,
        summary=summary,
        ideas=ideas,
        papers=papers,
        models=models,
        datasets=datasets,
        tweets=tweets,
    )
    md_path = daily_report_path(date, "md")
    write_text(md_path, md_content)
    logger.info("Daily markdown report written to %s", md_path)

    # On Sundays, also generate weekly ideas summary
    if datetime.utcnow().weekday() == 6:
        logger.info("It's Sunday — generating weekly ideas summary")
        from scripts.summarization.ideas_extractor import generate_weekly_summary

        generate_weekly_summary()

    logger.info("Daily aggregation complete for %s", date)
    return report_data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_daily_aggregation()
