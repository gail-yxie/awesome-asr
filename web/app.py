"""Flask web application for displaying ASR daily trends, podcasts, and mindmaps."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

import markdown
from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from google import genai
from google.genai import types

from scripts.chat.tools import GEMINI_TOOLS, handle_tool_call
from scripts.config import config

logger = logging.getLogger(__name__)

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DAILY_DIR = PROJECT_ROOT / "daily"
DATA_DIR = PROJECT_ROOT / "data"
PODCASTS_DIR = PROJECT_ROOT / "podcasts"
MINDMAPS_DIR = PROJECT_ROOT / "mindmaps"


def _load_daily_reports(limit: int = 30) -> list[dict]:
    """Load daily JSON reports, most recent first."""
    reports = []
    for path in sorted(DAILY_DIR.glob("????-??-??.json"), reverse=True)[:limit]:
        with open(path) as f:
            reports.append(json.load(f))
    return reports


def _load_daily_report(date: str) -> dict | None:
    """Load a single daily report by date string."""
    path = DAILY_DIR / f"{date}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _load_podcast_index() -> list[dict]:
    """Parse podcasts/index.md to get episode list."""
    index_path = PODCASTS_DIR / "index.md"
    if not index_path.exists():
        return []

    episodes = []
    for line in index_path.read_text().splitlines():
        if line.startswith("|") and not line.startswith("| Episode") and "---" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 3:
                # Extract URL from markdown link
                audio_link = parts[2]
                url = ""
                if "(" in audio_link:
                    url = audio_link.split("(")[1].rstrip(")")
                episodes.append(
                    {
                        "episode": parts[0],
                        "date": parts[1],
                        "audio_url": url,
                    }
                )
    return episodes


@app.route("/")
def index():
    """Dashboard: today's summary, recent highlights, latest podcast."""
    reports = _load_daily_reports(limit=7)
    latest = reports[0] if reports else None
    podcasts = _load_podcast_index()
    latest_podcast = podcasts[0] if podcasts else None

    return render_template(
        "index.html",
        latest_report=latest,
        recent_reports=reports[:5],
        latest_podcast=latest_podcast,
    )


@app.route("/daily")
def daily_list():
    """Paginated list of all daily reports."""
    reports = _load_daily_reports(limit=100)
    return render_template("daily_list.html", reports=reports)


@app.route("/daily/<date>")
def daily_detail(date: str):
    """Single daily report view."""
    report = _load_daily_report(date)
    if report is None:
        abort(404)

    # Also try to load the markdown version for rich rendering
    md_path = DAILY_DIR / f"{date}.md"
    html_content = ""
    if md_path.exists():
        html_content = markdown.markdown(
            md_path.read_text(),
            extensions=["tables", "fenced_code"],
        )

    return render_template(
        "daily.html",
        report=report,
        html_content=html_content,
    )


@app.route("/podcasts")
def podcasts():
    """Podcast episodes listing."""
    episodes = _load_podcast_index()

    # Also list script files
    scripts = sorted(PODCASTS_DIR.glob("*-script.md"), reverse=True)
    script_map = {}
    for s in scripts:
        key = s.stem.replace("-script", "")
        script_map[key] = markdown.markdown(s.read_text())

    return render_template(
        "podcasts.html",
        episodes=episodes,
        script_map=script_map,
    )


@app.route("/leaderboard")
def leaderboard():
    """Open ASR Leaderboard top models."""
    lb_path = DATA_DIR / "leaderboard.json"
    lb_data = {"last_updated": None, "models": []}
    if lb_path.exists():
        with open(lb_path) as f:
            lb_data = json.load(f)
    return render_template("leaderboard.html", leaderboard=lb_data)


@app.route("/models")
def models():
    """Open-source ASR models catalog."""
    models_path = DATA_DIR / "models.json"
    model_list = []
    if models_path.exists():
        with open(models_path) as f:
            model_list = json.load(f)
    return render_template("models.html", models=model_list)


@app.route("/mindmaps")
def mindmaps():
    """Mindmap viewer."""
    html_files = sorted(MINDMAPS_DIR.glob("*.html"))
    maps = [{"name": f.stem, "filename": f.name} for f in html_files]
    return render_template("mindmaps.html", maps=maps)


@app.route("/podcasts/audio/<filename>")
def serve_podcast_audio(filename: str):
    """Serve a podcast audio file."""
    return send_from_directory(str(PODCASTS_DIR), filename)


@app.route("/mindmaps/<filename>")
def serve_mindmap(filename: str):
    """Serve a mindmap HTML file."""
    return send_from_directory(str(MINDMAPS_DIR), filename)


# ── Chat ──

SYSTEM_INSTRUCTION = """You are an ASR (Automatic Speech Recognition) research assistant for the Awesome ASR project.
You help users explore recent papers, models, leaderboards, and generate content like podcasts and mindmaps.

When answering questions:
- Use the available tools to fetch real data before responding.
- Be concise but informative.
- When listing papers or models, format them clearly with titles and links.
- For generation tasks (daily report, podcast, mindmaps, deep-dive), let the user know these take time.
- You can save and retrieve personal research notes for the user.

Available data sources:
- Daily reports with arXiv papers and HuggingFace models
- Open ASR Leaderboard (ESB benchmark, WER scores)
- Model catalog with architecture and download info
- Personal notes stored locally
"""

MAX_TOOL_ROUNDS = 5


@app.route("/chat")
def chat():
    """Chat assistant page."""
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle chat messages with Gemini function calling."""
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Missing messages"}), 400

    messages = data["messages"]
    if not messages:
        return jsonify({"error": "Empty messages"}), 400

    # Build contents for Gemini
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        parts = []
        for part in msg.get("parts", []):
            if "text" in part:
                parts.append(types.Part.from_text(text=part["text"]))
        if parts:
            contents.append(types.Content(role=role, parts=parts))

    client = genai.Client(api_key=config.gemini_api_key)
    tools_used = []

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.models.generate_content(
                model=config.gemini_chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=GEMINI_TOOLS,
                ),
            )

            # Check for function calls
            function_calls = [
                part for part in response.candidates[0].content.parts
                if part.function_call
            ]

            if not function_calls:
                # Pure text response — done
                reply = response.text or ""
                return jsonify({"reply": reply, "tools_used": tools_used})

            # Execute each tool call and build responses
            contents.append(response.candidates[0].content)

            fn_response_parts = []
            for part in function_calls:
                fc = part.function_call
                tools_used.append(fc.name)
                logger.info("Chat tool call: %s(%s)", fc.name, fc.args)
                result = handle_tool_call(fc.name, dict(fc.args))
                fn_response_parts.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response=result,
                    )
                )

            contents.append(types.Content(role="user", parts=fn_response_parts))

        # Exhausted rounds — return last text
        reply = response.text or "I ran out of steps processing your request. Please try a simpler question."
        return jsonify({"reply": reply, "tools_used": tools_used})

    except Exception as e:
        logger.exception("Chat API error")
        return jsonify({"error": str(e)}), 500


# ── Chat Sessions ──

SESSIONS_PATH = DATA_DIR / "chat_sessions.json"


def _load_sessions() -> list[dict]:
    if SESSIONS_PATH.exists():
        with open(SESSIONS_PATH) as f:
            return json.load(f)
    return []


def _save_sessions(sessions: list[dict]) -> None:
    SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_PATH, "w") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


@app.route("/api/chat/sessions", methods=["GET"])
def list_sessions():
    """List all chat sessions (id, title, updated), most recent first."""
    sessions = _load_sessions()
    # Return lightweight list without full messages
    summary = [
        {"id": s["id"], "title": s["title"], "updated": s["updated"]}
        for s in sorted(sessions, key=lambda x: x["updated"], reverse=True)
    ]
    return jsonify({"sessions": summary})


@app.route("/api/chat/sessions", methods=["POST"])
def create_session():
    """Create a new chat session."""
    session = {
        "id": str(uuid.uuid4())[:8],
        "title": "New Chat",
        "created": datetime.utcnow().isoformat(),
        "updated": datetime.utcnow().isoformat(),
        "messages": [],
    }
    sessions = _load_sessions()
    sessions.append(session)
    _save_sessions(sessions)
    return jsonify(session)


@app.route("/api/chat/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Get a full chat session with messages."""
    sessions = _load_sessions()
    for s in sessions:
        if s["id"] == session_id:
            return jsonify(s)
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/chat/sessions/<session_id>", methods=["PUT"])
def update_session(session_id: str):
    """Update a session's messages and title."""
    data = request.get_json()
    sessions = _load_sessions()
    for s in sessions:
        if s["id"] == session_id:
            if "messages" in data:
                s["messages"] = data["messages"]
            if "title" in data:
                s["title"] = data["title"]
            s["updated"] = datetime.utcnow().isoformat()
            _save_sessions(sessions)
            return jsonify(s)
    return jsonify({"error": "Session not found"}), 404


@app.route("/api/chat/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Delete a chat session."""
    sessions = _load_sessions()
    new_sessions = [s for s in sessions if s["id"] != session_id]
    if len(new_sessions) == len(sessions):
        return jsonify({"error": "Session not found"}), 404
    _save_sessions(new_sessions)
    return jsonify({"status": "deleted"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
