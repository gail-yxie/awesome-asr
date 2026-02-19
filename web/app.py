"""Flask web application for displaying ASR daily trends, podcasts, and mindmaps."""

import base64
import json
import logging
import queue
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

import markdown
from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory
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


MEDIA_PATH = DATA_DIR / "model_media.json"
NOTES_PATH = DATA_DIR / "model_notes.json"
PODCAST_NAMES_PATH = DATA_DIR / "podcast_names.json"

# ── Podcast keyword highlighting ──

PODCAST_KEYWORDS = [
    # Architecture & methods
    "Mixture-of-Experts", "MoE", "CTC", "Encoder-Decoder", "Transducer",
    "autoregressive", "non-autoregressive", "Thinker-Talker",
    "multi-codebook", "flash attention", "window attention",
    "block-wise", "Rotary Position Embedding", "KV cache",
    "Fbank", "downsampling", "token rate",
    # Training & optimisation techniques
    "contrastive learning", "supervised fine-tuning", "SFT",
    "reinforcement learning", "GSPO", "pseudo-labeled",
    "context biasing", "domain adaptation", "pretraining",
    "noise robustness", "instruction injection",
    # Innovation concepts
    "Large Audio-Language Model", "LALM", "native audio processing",
    "multimodal", "foundation model", "end-to-end",
    "semantic-acoustic", "embedding space", "depth-aware",
    "modality tax", "on-device", "edge-device",
    "intent recognition", "Audio Reasoning",
    # ASR-specific expert terms
    "forced alignment", "forced aligner", "word-level timestamps",
    "phoneme", "phonetic decoding", "acoustic variability",
    "code-switching", "disfluency", "paraphasia",
    "long-form audio", "streaming inference",
    "first-packet latency", "Time-to-First-Token",
    # Metrics
    "Word Error Rate", "WER", "Real-Time Factor", "RTF",
    "state-of-the-art",
]

_kw_pattern = re.compile(
    r"\b("
    + "|".join(re.escape(kw) for kw in sorted(PODCAST_KEYWORDS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def _highlight_keywords(text: str) -> str:
    """Wrap recognised ASR keywords in <mark> tags."""
    return _kw_pattern.sub(r'<mark class="keyword">\1</mark>', text)


def _render_podcast_script(raw_text: str) -> str:
    """Convert a podcast script markdown file to styled HTML with dialogue blocks."""
    import html as html_mod

    lines = raw_text.strip().split("\n")
    header_lines: list[str] = []
    body_lines: list[str] = []

    # Separate header (title + optional metadata) from dialogue
    in_header = True
    for line in lines:
        if in_header:
            if line.startswith("#") or line.startswith("*") or line.strip() == "":
                header_lines.append(line)
            else:
                in_header = False
                body_lines.append(line)
        else:
            body_lines.append(line)

    # Render header via markdown
    header_html = markdown.markdown("\n".join(header_lines)) if header_lines else ""

    # Parse dialogue paragraphs (split on blank lines)
    paragraphs = "\n".join(body_lines).split("\n\n")
    dialogue_html_parts: list[str] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if para.startswith("Host:"):
            speaker = "host"
            label = "Host"
            text = para[5:].strip()
        elif para.startswith("Guest:"):
            speaker = "guest"
            label = "Guest"
            text = para[6:].strip()
        else:
            # Non-dialogue paragraph (metadata, etc.)
            safe_text = html_mod.escape(para)
            safe_text = _highlight_keywords(safe_text)
            dialogue_html_parts.append(f'<p class="script-meta">{safe_text}</p>')
            continue

        safe_text = html_mod.escape(text)
        safe_text = _highlight_keywords(safe_text)
        dialogue_html_parts.append(
            f'<div class="dialogue dialogue-{speaker}">'
            f'<span class="speaker-label">{label}</span>'
            f"<p>{safe_text}</p>"
            f"</div>"
        )

    return header_html + "\n".join(dialogue_html_parts)


def _model_slug(name: str) -> str:
    """Generate a URL-safe slug from a model name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug).strip("-")
    return slug


def _extract_arxiv_id(paper_url: str) -> str | None:
    """Extract arXiv ID from a paper URL."""
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


def _load_model_media() -> dict:
    if MEDIA_PATH.exists():
        with open(MEDIA_PATH) as f:
            return json.load(f)
    return {}


def _load_model_notes() -> dict:
    if NOTES_PATH.exists():
        with open(NOTES_PATH) as f:
            return json.load(f)
    return {}


def _load_podcast_names() -> dict:
    if PODCAST_NAMES_PATH.exists():
        with open(PODCAST_NAMES_PATH) as f:
            return json.load(f)
    return {}


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

    # Render script files with dialogue blocks and keyword highlights
    scripts = sorted(PODCASTS_DIR.glob("*-script.md"), reverse=True)
    script_map = {}
    for s in scripts:
        key = s.stem.replace("-script", "")
        script_map[key] = _render_podcast_script(s.read_text())

    podcast_names = _load_podcast_names()

    return render_template(
        "podcasts.html",
        episodes=episodes,
        script_map=script_map,
        podcast_names=podcast_names,
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

    media = _load_model_media()
    notes = _load_model_notes()

    for m in model_list:
        slug = _model_slug(m["name"])
        m["slug"] = slug

        # Attach podcast/mindmap URLs if generated for this paper
        arxiv_id = _extract_arxiv_id(m.get("paper_url", ""))
        m["arxiv_id"] = arxiv_id or ""
        if arxiv_id and arxiv_id in media:
            entry = media[arxiv_id]
            if entry.get("podcast_audio"):
                m["podcast_url"] = f"/podcasts/audio/{entry['podcast_audio']}"
            if entry.get("mindmap_html"):
                m["mindmap_url"] = f"/mindmaps/{entry['mindmap_html']}"

        # Attach notes
        m["notes"] = notes.get(slug, {}).get("text", "")

    return render_template("models.html", models=model_list)


@app.route("/mindmaps")
def mindmaps():
    """Mindmap viewer."""
    html_files = sorted(MINDMAPS_DIR.glob("*.html"))
    maps = [{"name": f.stem, "filename": f.name} for f in html_files]
    return render_template("mindmaps.html", maps=maps)


GITHUB_REPO_SLUG = "gail-yxie/awesome-asr"
GITHUB_RELEASE_TAG = "podcast-audio"


@app.route("/podcasts/audio/<filename>")
def serve_podcast_audio(filename: str):
    """Serve a podcast audio file, falling back to a GitHub Release download."""
    local_path = PODCASTS_DIR / filename
    if local_path.exists():
        return send_from_directory(str(PODCASTS_DIR), filename)

    # Redirect to GitHub Release asset
    from flask import redirect

    gh_url = (
        f"https://github.com/{GITHUB_REPO_SLUG}/releases/download/"
        f"{GITHUB_RELEASE_TAG}/{filename}"
    )
    return redirect(gh_url, code=302)


@app.route("/mindmaps/<filename>")
def serve_mindmap(filename: str):
    """Serve a mindmap HTML file."""
    return send_from_directory(str(MINDMAPS_DIR), filename)


# ── Model Notes API ──


@app.route("/api/models/<slug>/notes", methods=["POST"])
def save_model_notes(slug: str):
    """Save personal notes for a specific model."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    notes = _load_model_notes()
    notes[slug] = {
        "text": data["text"],
        "updated_at": datetime.utcnow().isoformat(),
    }

    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_PATH, "w") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "saved", "slug": slug})


# ── Model Media Generation API ──


@app.route("/api/models/generate", methods=["POST"])
def generate_model_media():
    """Generate podcast and mindmap for a model's paper via SSE streaming."""
    data = request.get_json()
    if not data or "arxiv_id" not in data:
        return jsonify({"error": "Missing 'arxiv_id' field"}), 400

    arxiv_id = data["arxiv_id"]

    def generate():
        from scripts.deep_dive.pipeline import run_pipeline
        from scripts.deep_dive.paper_fetcher import parse_arxiv_input
        from scripts.utils import write_json, read_json

        progress_q = queue.Queue()

        def on_progress(step):
            progress_q.put(step)

        result_holder = [None, None]  # [result, exception]

        def _run():
            try:
                result_holder[0] = run_pipeline(
                    arxiv_input=arxiv_id,
                    on_progress=on_progress,
                )
            except Exception as exc:
                result_holder[1] = exc

        t = threading.Thread(target=_run)
        t.start()

        while t.is_alive():
            try:
                step = progress_q.get(timeout=0.5)
                yield _sse_event({"type": "progress", "label": step})
            except queue.Empty:
                pass

        # Drain remaining
        while not progress_q.empty():
            step = progress_q.get_nowait()
            yield _sse_event({"type": "progress", "label": step})

        if result_holder[1]:
            yield _sse_event({"type": "error", "message": str(result_holder[1])})
            return

        result = result_holder[0]
        paper = result["paper"]
        parsed_id = parse_arxiv_input(arxiv_id)

        # Update model_media.json
        media = read_json(MEDIA_PATH) if MEDIA_PATH.exists() else {}
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
        media[parsed_id] = entry
        write_json(MEDIA_PATH, media)

        # Build URLs for client to update buttons
        urls = {}
        if entry.get("podcast_audio"):
            urls["podcast_url"] = f"/podcasts/audio/{entry['podcast_audio']}"
        if entry.get("mindmap_html"):
            urls["mindmap_url"] = f"/mindmaps/{entry['mindmap_html']}"

        yield _sse_event({
            "type": "done",
            "title": paper.title,
            "urls": urls,
        })

    return Response(generate(), mimetype="text/event-stream")


# ── Podcast Names API ──


@app.route("/api/podcast-name/<path:episode>", methods=["POST"])
def save_podcast_name(episode: str):
    """Save a custom display name for a podcast episode."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Missing 'name' field"}), 400

    names = _load_podcast_names()
    name_text = data["name"].strip()
    if name_text:
        names[episode] = {
            "name": name_text,
            "updated_at": datetime.utcnow().isoformat(),
        }
    else:
        names.pop(episode, None)

    PODCAST_NAMES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PODCAST_NAMES_PATH, "w") as f:
        json.dump(names, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "saved", "episode": episode})


# ── Chat ──

SYSTEM_INSTRUCTION = """You are an ASR (Automatic Speech Recognition) research assistant for the Awesome ASR project.
You help users explore recent papers, models, leaderboards, and generate content like podcasts and mindmaps.

When answering questions:
- Use the available tools to fetch real data before responding.
- Be concise but informative.
- When listing papers or models, format them clearly with titles and links.
- For generation tasks (daily report, podcast, mindmaps, deep-dive), let the user know these take time.
- You can save and retrieve personal research notes for the user.
- When asked to generate a podcast or mindmap for a model by name, use list_models to find the model first, extract the arXiv ID from its paper_url, then call generate_deep_dive with that arXiv ID. Do NOT ask the user for the arXiv ID if the model is in the catalog.
- Users may send voice messages (audio). Listen to the audio and respond to their spoken request just like a text message.

Available data sources:
- Daily reports with arXiv papers and HuggingFace models
- Open ASR Leaderboard (ESB benchmark, WER scores)
- Model catalog with architecture, paper_url (arXiv), and model_url (HuggingFace)
- Personal notes stored locally
"""

MAX_TOOL_ROUNDS = 5


@app.route("/chat")
def chat():
    """Chat assistant page."""
    return render_template("chat.html")


TOOL_LABELS = {
    "search_papers": "Searching papers",
    "get_daily_report": "Loading daily report",
    "get_leaderboard": "Fetching leaderboard",
    "list_models": "Looking up models",
    "generate_daily_report": "Generating daily report",
    "generate_podcast": "Generating podcast",
    "generate_mindmaps": "Generating mindmaps",
    "generate_deep_dive": "Generating deep-dive",
    "generate_all_model_media": "Generating all model media",
    "save_note": "Saving note",
    "list_notes": "Loading notes",
    "delete_note": "Deleting note",
}

# Tools that support the _progress_cb parameter for sub-step reporting
TOOLS_WITH_PROGRESS = {"generate_deep_dive"}


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle chat messages with streaming progress via SSE."""
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Missing messages"}), 400

    messages = data["messages"]
    if not messages:
        return jsonify({"error": "Empty messages"}), 400

    # Extract optional audio attachment
    audio_data = data.get("audio")  # {data: base64, mime_type: "audio/webm"}

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

    # Append audio to the last user message if present
    if audio_data and contents:
        audio_bytes = base64.b64decode(audio_data["data"])
        mime_type = audio_data.get("mime_type", "audio/webm")
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        # Add to the last user content
        for i in range(len(contents) - 1, -1, -1):
            if contents[i].role == "user":
                contents[i].parts.append(audio_part)
                break

    def generate():
        client = genai.Client(api_key=config.gemini_api_key)
        tools_used = []

        try:
            yield _sse_event({"type": "thinking", "message": "Thinking..."})

            for round_num in range(MAX_TOOL_ROUNDS):
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
                    reply = response.text or ""
                    yield _sse_event({
                        "type": "reply",
                        "text": reply,
                        "tools_used": tools_used,
                    })
                    return

                contents.append(response.candidates[0].content)

                fn_response_parts = []
                for part in function_calls:
                    fc = part.function_call
                    tool_name = fc.name
                    tools_used.append(tool_name)
                    label = TOOL_LABELS.get(tool_name, tool_name)

                    yield _sse_event({
                        "type": "tool_start",
                        "tool": tool_name,
                        "label": f"{label}...",
                    })

                    logger.info("Chat tool call: %s(%s)", fc.name, fc.args)
                    tool_args = dict(fc.args)

                    if tool_name in TOOLS_WITH_PROGRESS:
                        # Run in thread with progress queue for sub-step events
                        progress_q = queue.Queue()
                        tool_result_holder = [None, None]  # [result, exception]

                        def _run_tool(q=progress_q, h=tool_result_holder,
                                      n=tool_name, a=tool_args):
                            a["_progress_cb"] = lambda step: q.put(step)
                            try:
                                h[0] = handle_tool_call(n, a)
                            except Exception as exc:
                                h[1] = exc

                        t = threading.Thread(target=_run_tool)
                        t.start()
                        while t.is_alive():
                            try:
                                step = progress_q.get(timeout=0.5)
                                yield _sse_event({
                                    "type": "substep",
                                    "label": f"{step}...",
                                })
                            except queue.Empty:
                                pass
                        # Drain remaining events
                        while not progress_q.empty():
                            step = progress_q.get_nowait()
                            yield _sse_event({
                                "type": "substep",
                                "label": f"{step}...",
                            })
                        if tool_result_holder[1]:
                            raise tool_result_holder[1]
                        result = tool_result_holder[0]
                    else:
                        result = handle_tool_call(tool_name, tool_args)

                    yield _sse_event({
                        "type": "tool_done",
                        "tool": tool_name,
                        "label": label,
                    })

                    fn_response_parts.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response=result,
                        )
                    )

                contents.append(types.Content(role="user", parts=fn_response_parts))

                if round_num < MAX_TOOL_ROUNDS - 1:
                    yield _sse_event({
                        "type": "thinking",
                        "message": "Analyzing results...",
                    })

            reply = response.text or "I ran out of steps processing your request. Please try a simpler question."
            yield _sse_event({
                "type": "reply",
                "text": reply,
                "tools_used": tools_used,
            })

        except Exception as e:
            logger.exception("Chat API error")
            yield _sse_event({"type": "error", "message": str(e)})

    return Response(generate(), mimetype="text/event-stream")


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
