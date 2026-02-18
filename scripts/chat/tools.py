"""Chat tool declarations and execution handlers for Gemini function calling."""

import json
import logging
from datetime import datetime, timedelta

from google.genai import types

from scripts.utils import DAILY_DIR, DATA_DIR, read_json, write_json, list_daily_json_reports

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool declarations
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS = [
    # Research & Data
    types.FunctionDeclaration(
        name="search_papers",
        description="Search recent daily reports for ASR papers matching a query. Returns matching papers with title, authors, abstract, and URL.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search query to match against paper titles and abstracts.",
                },
                "days_back": {
                    "type": "INTEGER",
                    "description": "Number of days to search back. Default 7.",
                },
            },
            "required": ["query"],
        },
    ),
    types.FunctionDeclaration(
        name="get_daily_report",
        description="Get the full daily report for a specific date, including papers, models, summary, and ideas.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "date": {
                    "type": "STRING",
                    "description": "Date in YYYY-MM-DD format.",
                },
            },
            "required": ["date"],
        },
    ),
    types.FunctionDeclaration(
        name="get_leaderboard",
        description="Get the Open ASR Leaderboard showing top models ranked by Word Error Rate (WER) on standard benchmarks.",
        parameters={"type": "OBJECT", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="list_models",
        description="List or search open-source ASR models from the catalog. Returns model name, date, architecture, downloads, and links.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Optional search query to filter models by name or architecture.",
                },
            },
        },
    ),
    # Generation
    types.FunctionDeclaration(
        name="generate_daily_report",
        description="Run the daily tracking pipeline to fetch the latest ASR papers from arXiv and models from HuggingFace. This takes about 1-2 minutes.",
        parameters={"type": "OBJECT", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="generate_podcast",
        description="Generate a weekly podcast episode summarizing recent ASR developments. This takes several minutes.",
        parameters={"type": "OBJECT", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="generate_mindmaps",
        description="Regenerate the ASR taxonomy mindmaps (overview, papers, models). This takes about 1-2 minutes.",
        parameters={"type": "OBJECT", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="generate_deep_dive",
        description="Generate a deep-dive podcast and mindmap for a specific arXiv paper. Provide the arXiv ID and optionally HuggingFace model IDs and GitHub URL.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "arxiv_id": {
                    "type": "STRING",
                    "description": "arXiv paper ID (e.g., '2601.21337') or URL.",
                },
                "hf_models": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Optional list of HuggingFace model IDs related to the paper.",
                },
                "github_url": {
                    "type": "STRING",
                    "description": "Optional GitHub repository URL.",
                },
            },
            "required": ["arxiv_id"],
        },
    ),
    # Notes
    types.FunctionDeclaration(
        name="save_note",
        description="Save a personal research note. Notes are stored locally and can be retrieved later.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Title of the note.",
                },
                "content": {
                    "type": "STRING",
                    "description": "Content of the note (plain text or markdown).",
                },
            },
            "required": ["title", "content"],
        },
    ),
    types.FunctionDeclaration(
        name="list_notes",
        description="List all saved personal research notes.",
        parameters={"type": "OBJECT", "properties": {}},
    ),
    types.FunctionDeclaration(
        name="delete_note",
        description="Delete a personal research note by title.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Title of the note to delete.",
                },
            },
            "required": ["title"],
        },
    ),
]

GEMINI_TOOLS = [types.Tool(function_declarations=TOOL_DECLARATIONS)]

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

NOTES_PATH = DATA_DIR / "notes.json"


def _load_notes() -> list[dict]:
    if NOTES_PATH.exists():
        return read_json(NOTES_PATH)
    return []


def _save_notes(notes: list[dict]) -> None:
    write_json(NOTES_PATH, notes)


def handle_tool_call(name: str, args: dict) -> dict:
    """Execute a tool by name and return the result dict."""
    try:
        handler = HANDLERS.get(name)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        return handler(**args)
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return {"error": str(e)}


# --- Research & Data handlers ---

def _search_papers(query: str, days_back: int = 7) -> dict:
    query_lower = query.lower()
    matches = []
    for path in list_daily_json_reports(days=days_back):
        report = read_json(path)
        for paper in report.get("papers", []):
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            if query_lower in title.lower() or query_lower in abstract.lower():
                matches.append({
                    "title": title,
                    "authors": paper.get("authors", []),
                    "abstract": abstract[:500],
                    "url": paper.get("url", ""),
                    "date": report.get("date", ""),
                })
    return {"papers": matches, "count": len(matches)}


def _get_daily_report(date: str) -> dict:
    path = DAILY_DIR / f"{date}.json"
    if not path.exists():
        return {"error": f"No report found for {date}"}
    report = read_json(path)
    # Truncate for context window
    for paper in report.get("papers", []):
        if len(paper.get("abstract", "")) > 500:
            paper["abstract"] = paper["abstract"][:500] + "..."
    return report


def _get_leaderboard() -> dict:
    lb_path = DATA_DIR / "leaderboard.json"
    if not lb_path.exists():
        return {"error": "Leaderboard data not found"}
    return read_json(lb_path)


def _list_models(query: str | None = None) -> dict:
    models_path = DATA_DIR / "models.json"
    if not models_path.exists():
        return {"models": [], "count": 0}
    models = read_json(models_path)
    if query:
        query_lower = query.lower()
        models = [
            m for m in models
            if query_lower in m.get("model_id", "").lower()
            or query_lower in m.get("architecture", "").lower()
        ]
    # Limit to top 20 for context window
    return {"models": models[:20], "count": len(models)}


# --- Generation handlers ---

def _generate_daily_report() -> dict:
    from scripts.tracking.aggregator import run_daily_aggregation
    result = run_daily_aggregation()
    return {
        "status": "success",
        "date": result.get("date", ""),
        "papers_count": len(result.get("papers", [])),
        "models_count": len(result.get("new_models", [])),
    }


def _generate_podcast() -> dict:
    from scripts.podcast.script_generator import generate_script
    from scripts.podcast.tts_engine import generate_audio

    script = generate_script()
    if not script:
        return {"status": "error", "message": "Failed to generate script"}
    audio_path = generate_audio(script_text=script)
    return {
        "status": "success",
        "has_audio": audio_path is not None,
        "audio_file": str(audio_path) if audio_path else None,
    }


def _generate_mindmaps() -> dict:
    from scripts.mindmap.taxonomy_builder import generate_mindmap_markdown
    from scripts.mindmap.markmap_renderer import render_mindmaps

    generate_mindmap_markdown()
    html_paths = render_mindmaps()
    return {
        "status": "success",
        "mindmaps": [p.name for p in html_paths],
    }


def _generate_deep_dive(
    arxiv_id: str,
    hf_models: list[str] | None = None,
    github_url: str | None = None,
) -> dict:
    from scripts.deep_dive.pipeline import run_pipeline

    result = run_pipeline(
        arxiv_input=arxiv_id,
        hf_models=hf_models,
        github_url=github_url,
        skip_audio=False,
        skip_mindmap=False,
    )
    paper = result["paper"]
    return {
        "status": "success",
        "title": paper.title,
        "script_path": str(result["script_path"]),
        "has_audio": result["audio_path"] is not None,
        "has_mindmap": result["mindmap_html_path"] is not None,
    }


# --- Notes handlers ---

def _save_note(title: str, content: str) -> dict:
    notes = _load_notes()
    # Update existing or append
    for note in notes:
        if note["title"] == title:
            note["content"] = content
            note["updated"] = datetime.utcnow().isoformat()
            _save_notes(notes)
            return {"status": "updated", "title": title}
    notes.append({
        "title": title,
        "content": content,
        "created": datetime.utcnow().isoformat(),
        "updated": datetime.utcnow().isoformat(),
    })
    _save_notes(notes)
    return {"status": "created", "title": title}


def _list_notes() -> dict:
    notes = _load_notes()
    return {"notes": notes, "count": len(notes)}


def _delete_note(title: str) -> dict:
    notes = _load_notes()
    original_len = len(notes)
    notes = [n for n in notes if n["title"] != title]
    if len(notes) == original_len:
        return {"error": f"Note '{title}' not found"}
    _save_notes(notes)
    return {"status": "deleted", "title": title}


# Handler registry
HANDLERS = {
    "search_papers": _search_papers,
    "get_daily_report": _get_daily_report,
    "get_leaderboard": _get_leaderboard,
    "list_models": _list_models,
    "generate_daily_report": _generate_daily_report,
    "generate_podcast": _generate_podcast,
    "generate_mindmaps": _generate_mindmaps,
    "generate_deep_dive": _generate_deep_dive,
    "save_note": _save_note,
    "list_notes": _list_notes,
    "delete_note": _delete_note,
}
