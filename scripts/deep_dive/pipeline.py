"""Paper deep-dive pipeline: fetch, script, audio, mindmap, index.

Usage:
    python -m scripts.deep_dive.pipeline --arxiv 2601.21337
    python -m scripts.deep_dive.pipeline --arxiv https://arxiv.org/abs/2601.21337 \\
        --hf Qwen/Qwen3-ASR-1.7B Qwen/Qwen3-ASR-0.6B \\
        --github https://github.com/QwenLM/Qwen3-ASR
    python -m scripts.deep_dive.pipeline --arxiv 2601.21337 --no-audio
"""

import argparse
import logging

import shutil
import subprocess

from scripts.deep_dive.paper_fetcher import (
    PaperInfo,
    fetch_full_text,
    fetch_paper,
    parse_arxiv_input,
)
from scripts.deep_dive.mindmap_generator import generate_paper_mindmap
from scripts.deep_dive.script_generator import generate_deep_dive_script
from scripts.mindmap.markmap_renderer import render_single_mindmap
from scripts.podcast.tts_engine import generate_audio
from scripts.utils import MINDMAPS_DIR, PODCASTS_DIR, read_text, retry, today_str, write_text

GITHUB_REPO_SLUG = "gail-yxie/awesome-asr"
GITHUB_RELEASE_TAG = "podcast-audio"

logger = logging.getLogger(__name__)


def _upload_to_github_release(audio_path: "Path") -> bool:
    """Upload an audio file to the GitHub Release, creating the release if needed.

    Returns True on success, False if gh CLI is unavailable or upload fails.
    """
    if not shutil.which("gh"):
        logger.warning("gh CLI not found; skipping GitHub Release upload")
        return False

    # Ensure the release exists
    subprocess.run(
        [
            "gh", "release", "create", GITHUB_RELEASE_TAG,
            "--repo", GITHUB_REPO_SLUG,
            "--title", "Podcast Audio",
            "--notes", "Auto-generated podcast audio files.",
        ],
        capture_output=True,
    )

    # Upload (--clobber overwrites if the asset already exists)
    result = subprocess.run(
        [
            "gh", "release", "upload", GITHUB_RELEASE_TAG,
            str(audio_path), "--clobber",
            "--repo", GITHUB_REPO_SLUG,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        logger.info("Uploaded %s to GitHub Release %s", audio_path.name, GITHUB_RELEASE_TAG)
        return True
    logger.warning("GitHub Release upload failed: %s", result.stderr)
    return False


def _update_podcast_index(slug: str, date: str) -> None:
    """Append a deep-dive episode row to podcasts/index.md."""
    index_path = PODCASTS_DIR / "index.md"
    if index_path.exists():
        content = read_text(index_path)
    else:
        content = "# ASR Podcast Episodes\n\n| Episode | Date | Audio |\n|---------|------|-------|\n"

    entry = f"| {slug}-deep-dive | {date} | [Listen](/podcasts/audio/{slug}-deep-dive.mp3) |"
    if entry not in content:
        content = content.rstrip() + "\n" + entry + "\n"
        write_text(index_path, content)
        logger.info("Updated podcasts/index.md")


def run_pipeline(
    arxiv_input: str,
    hf_models: list[str] | None = None,
    github_url: str | None = None,
    skip_audio: bool = False,
    skip_mindmap: bool = False,
    on_progress: "callable | None" = None,
) -> dict:
    """Execute the full deep-dive pipeline.

    Args:
        arxiv_input: arXiv ID or URL.
        hf_models: Optional list of HuggingFace model IDs.
        github_url: Optional GitHub repository URL.
        skip_audio: If True, skip TTS generation.
        skip_mindmap: If True, skip mindmap generation.
        on_progress: Optional callback(step_label) called before each step.

    Returns:
        Dict with paths to generated artifacts.
    """
    def _progress(label: str) -> None:
        logger.info("--- %s ---", label)
        if on_progress:
            on_progress(label)

    # 1. Parse input and fetch paper
    _progress("Fetching paper metadata")
    arxiv_id = parse_arxiv_input(arxiv_input)
    paper = fetch_paper(arxiv_id)
    if hf_models:
        paper.hf_models = hf_models
    if github_url:
        paper.github_url = github_url

    # 2. Attempt full text extraction
    _progress("Extracting full text")
    paper.full_text = fetch_full_text(arxiv_id)

    # 3. Generate podcast script (with retry)
    _progress("Generating podcast script")
    script = retry(lambda: generate_deep_dive_script(paper))

    # 4. Generate audio (unless skipped)
    audio_path = None
    if not skip_audio and script:
        _progress("Generating audio (this takes a few minutes)")
        audio_path = retry(
            lambda: generate_audio(
                script_text=script,
                output_stem=f"{paper.slug}-deep-dive",
            )
        )
        if audio_path:
            _upload_to_github_release(audio_path)
            _update_podcast_index(paper.slug, today_str())

    # 5. Generate mindmap (unless skipped)
    mindmap_md_path = None
    mindmap_html_path = None
    if not skip_mindmap:
        _progress("Generating mindmap")
        mindmap_md_path = retry(lambda: generate_paper_mindmap(paper))
        if mindmap_md_path:
            _progress("Rendering mindmap to HTML")
            mindmap_html_path = render_single_mindmap(mindmap_md_path)

    return {
        "paper": paper,
        "script_path": PODCASTS_DIR / f"{paper.slug}-deep-dive-script.md",
        "audio_path": audio_path,
        "mindmap_md_path": mindmap_md_path,
        "mindmap_html_path": mindmap_html_path,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate a deep-dive podcast and mindmap for a single paper."
    )
    parser.add_argument(
        "--arxiv",
        required=True,
        help="arXiv paper ID or URL (e.g., 2601.21337 or https://arxiv.org/abs/2601.21337)",
    )
    parser.add_argument(
        "--hf",
        nargs="*",
        default=None,
        help="HuggingFace model IDs (e.g., Qwen/Qwen3-ASR-1.7B)",
    )
    parser.add_argument(
        "--github",
        default=None,
        help="GitHub repository URL",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip audio generation (script and mindmap only)",
    )
    parser.add_argument(
        "--no-mindmap",
        action="store_true",
        help="Skip mindmap generation",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    result = run_pipeline(
        arxiv_input=args.arxiv,
        hf_models=args.hf,
        github_url=args.github,
        skip_audio=args.no_audio,
        skip_mindmap=args.no_mindmap,
    )

    print(f"\nPaper: {result['paper'].title}")
    print(f"Script: {result['script_path']}")
    if result["audio_path"]:
        print(f"Audio: {result['audio_path']}")
    if result["mindmap_html_path"]:
        print(f"Mindmap: {result['mindmap_html_path']}")


if __name__ == "__main__":
    main()
