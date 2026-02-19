"""Render mindmap markdown files to interactive HTML using markmap-cli."""

import logging
import subprocess
from pathlib import Path

from scripts.utils import MINDMAPS_DIR

logger = logging.getLogger(__name__)

MINDMAP_FILES = [
    "asr-overview.md",
    "recent-papers.md",
    "models.md",
]


def render_single_mindmap(md_path: Path) -> Path | None:
    """Render a single mindmap markdown file to HTML using markmap-cli.

    Args:
        md_path: Path to the markdown file.

    Returns:
        Path to the generated HTML file, or None on failure.
    """
    html_path = md_path.with_suffix(".html")
    logger.info("Rendering %s → %s", md_path.name, html_path.name)

    try:
        subprocess.run(
            ["npx", "markmap-cli", str(md_path), "-o", str(html_path), "--no-open"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        logger.info("Generated %s", html_path)
        return html_path
    except FileNotFoundError:
        logger.error("markmap-cli not found. Install with: npm install -g markmap-cli")
        return None
    except subprocess.CalledProcessError as e:
        logger.error("markmap-cli failed for %s: %s", md_path.name, e.stderr)
        return None
    except subprocess.TimeoutExpired:
        logger.error("markmap-cli timed out for %s", md_path.name)
        return None


def render_mindmaps() -> list[Path]:
    """Render all mindmap markdown files to HTML using markmap-cli.

    Returns:
        List of generated HTML file paths.
    """
    generated = []

    for md_file in MINDMAP_FILES:
        md_path = MINDMAPS_DIR / md_file
        if not md_path.exists():
            logger.info("Skipping %s (not found)", md_file)
            continue

        result = render_single_mindmap(md_path)
        if result:
            generated.append(result)

    # Generate an index
    if generated:
        _generate_index(generated)

    return generated


def _generate_index(html_files: list[Path]) -> None:
    """Generate a simple index.md listing all mindmap HTML files."""
    lines = [
        "# ASR Mindmaps",
        "",
        "Interactive mindmaps exploring ASR topics. Open the HTML files in your browser.",
        "",
        "| Mindmap | Description |",
        "|---------|-------------|",
    ]

    descriptions = {
        "asr-overview.html": "Full ASR topic overview",
        "recent-papers.html": "Recent papers organized by category",
        "models.html": "ASR model landscape by author",
    }

    for path in html_files:
        desc = descriptions.get(path.name, path.name)
        lines.append(f"| [{path.name}]({path.name}) | {desc} |")

    index_path = MINDMAPS_DIR / "index.md"
    index_path.write_text("\n".join(lines) + "\n")
    logger.info("Generated mindmaps/index.md")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    render_mindmaps()
