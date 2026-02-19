"""Update README.md sections with data from generated reports and curated lists."""

import logging
import re

from scripts.utils import (
    DATA_DIR,
    PROJECT_ROOT,
    list_daily_json_reports,
    read_json,
    read_text,
    write_text,
)

logger = logging.getLogger(__name__)

README_PATH = PROJECT_ROOT / "README.md"


def _format_foundational_papers(papers: list[dict]) -> str:
    """Format foundational papers as a markdown list."""
    lines = []
    for p in papers:
        authors = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors += " et al."
        line = f"- **{p['title']}** ({p['year']}) — {p['description']}"
        if p.get("url"):
            line += f" [[Paper]({p['url']})]"
        lines.append(line)
    return "\n".join(lines)


def _format_recent_papers(reports: list[dict]) -> str:
    """Format recent papers from daily reports as a markdown table."""
    all_papers = []
    for report in reports:
        for paper in report.get("papers", []):
            all_papers.append(paper)

    if not all_papers:
        return "*No recent papers tracked yet. Daily tracking will populate this section automatically.*"

    # Deduplicate by title
    seen = set()
    unique = []
    for p in all_papers:
        key = p["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    lines = ["| Title | Authors | Date | Link |", "|-------|---------|------|------|"]
    for p in unique[:20]:
        authors = ", ".join(p["authors"][:2])
        if len(p["authors"]) > 2:
            authors += " et al."
        lines.append(
            f"| {p['title'][:80]} | {authors} | {p.get('published', 'N/A')} | [arXiv]({p['url']}) |"
        )
    return "\n".join(lines)


def _replace_section(readme: str, marker: str, content: str) -> str:
    """Replace content after a marker comment up to the next section heading."""
    pattern = re.compile(
        rf"({re.escape(marker)})\n(.*?)(?=\n###?\s|\n## |\Z)",
        re.DOTALL,
    )
    replacement = f"{marker}\n\n{content}\n"
    new_readme, count = pattern.subn(replacement, readme)
    if count == 0:
        logger.warning("Marker not found in README: %s", marker)
    return new_readme


def _format_leaderboard(models: list[dict]) -> str:
    """Format leaderboard top models as a markdown table."""
    lines = [
        "| Rank | Model | Avg WER |",
        "|------|-------|---------|",
    ]
    for m in models:
        mid = m["model_id"]
        lines.append(
            f"| {m['rank']} | [{mid}](https://huggingface.co/{mid}) | {m['avg_wer']}% |"
        )
    return "\n".join(lines)


def _replace_between_markers(readme: str, start: str, end: str, content: str) -> str:
    """Replace content between paired HTML comment markers."""
    pattern = re.compile(
        rf"({re.escape(start)})\n.*?\n({re.escape(end)})",
        re.DOTALL,
    )
    replacement = f"{start}\n{content}\n{end}"
    new_readme, count = pattern.subn(replacement, readme)
    if count == 0:
        logger.warning("Markers not found in README: %s ... %s", start, end)
    return new_readme


def update_readme() -> None:
    """Update README.md with foundational papers, recent papers, and leaderboard."""
    readme = read_text(README_PATH)

    # Update foundational papers
    foundational = read_json(DATA_DIR / "foundational_papers.json")
    foundational_content = _format_foundational_papers(foundational)
    readme = _replace_section(
        readme,
        "<!-- Add foundational ASR papers here -->",
        foundational_content,
    )

    # Update recent papers from daily reports
    report_paths = list_daily_json_reports(days=7)
    reports = [read_json(p) for p in report_paths]
    recent_content = _format_recent_papers(reports)
    readme = _replace_section(
        readme,
        "<!-- Recent papers will be auto-tracked and added here -->",
        recent_content,
    )

    # Update leaderboard top 10
    leaderboard_path = DATA_DIR / "leaderboard.json"
    if leaderboard_path.exists():
        lb_data = read_json(leaderboard_path)
        lb_content = _format_leaderboard(lb_data.get("models", []))
        readme = _replace_between_markers(
            readme,
            "<!-- leaderboard-top10-start -->",
            "<!-- leaderboard-top10-end -->",
            lb_content,
        )

    write_text(README_PATH, readme)
    logger.info("README.md updated successfully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_readme()
