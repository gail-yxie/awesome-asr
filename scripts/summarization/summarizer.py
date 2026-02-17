"""LLM-based summarization using Gemini 3 Pro Preview."""

import logging
import time

from google import genai

from scripts.config import config

logger = logging.getLogger(__name__)

DAILY_SUMMARY_PROMPT = """\
You are an expert in Automatic Speech Recognition (ASR) research.
Given today's new papers, models, and tweets, write a concise 3-5 sentence
summary highlighting the most significant developments. Focus on:
- The most impactful paper(s) and why they matter
- Any notable new model releases
- Emerging trends or connections between papers

Be specific and informative. Write for an audience of ASR researchers and practitioners.

## Today's Papers
{papers}

## New Models
{models}

## Twitter Highlights
{tweets}

Write your summary now (3-5 sentences, no headers):"""

IDEAS_PROMPT = """\
You are an expert in Automatic Speech Recognition (ASR) research.
Given today's papers, extract the key ideas and breakthroughs as a bullet-pointed list.
Each bullet should be a single, clear sentence describing one idea or finding.
Focus on novel techniques, surprising results, and practical implications.

## Papers
{papers}

Return 3-7 bullet points (just the text, no bullet markers):"""


def _get_client() -> genai.Client:
    return genai.Client(api_key=config.gemini_api_key)


def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with retry and exponential backoff."""
    client = _get_client()
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=config.gemini_model,
                contents=prompt,
            )
            return response.text.strip()
        except Exception:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            logger.warning(
                "Gemini API call failed (attempt %d/%d), retrying in %ds...",
                attempt + 1,
                max_retries,
                wait,
            )
            time.sleep(wait)


def _format_papers(papers: list[dict]) -> str:
    if not papers:
        return "No new papers today."
    lines = []
    for p in papers[:20]:
        authors = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors += " et al."
        lines.append(f"- {p['title']} ({authors})\n  {p['abstract'][:300]}...")
    return "\n".join(lines)


def _format_models(models: list[dict]) -> str:
    if not models:
        return "No new models today."
    return "\n".join(
        f"- {m['model_id']} by {m['author']} ({m['downloads']} downloads)"
        for m in models[:10]
    )


def _format_tweets(tweets: list[dict]) -> str:
    if not tweets:
        return "No tweets tracked."
    return "\n".join(f"- @{t['author']}: {t['text'][:200]}" for t in tweets[:10])


def summarize_daily(
    papers: list[dict],
    models: list[dict],
    tweets: list[dict],
) -> str:
    """Generate a 3-5 sentence summary of the day's ASR developments."""
    prompt = DAILY_SUMMARY_PROMPT.format(
        papers=_format_papers(papers),
        models=_format_models(models),
        tweets=_format_tweets(tweets),
    )
    return _call_gemini(prompt)


def extract_ideas(papers: list[dict]) -> list[str]:
    """Extract key ideas as bullet points from today's papers."""
    if not papers:
        return ["No new papers to analyze today."]

    prompt = IDEAS_PROMPT.format(papers=_format_papers(papers))
    response = _call_gemini(prompt)
    ideas = [
        line.strip().lstrip("•-*").strip()
        for line in response.split("\n")
        if line.strip()
    ]
    return ideas or ["No key ideas extracted."]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_papers = [
        {
            "title": "Test Paper",
            "authors": ["Author A"],
            "abstract": "A test abstract about ASR.",
        }
    ]
    print(summarize_daily(sample_papers, [], []))
