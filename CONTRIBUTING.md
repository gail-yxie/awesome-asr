# Contributing to Awesome ASR

Thank you for your interest in contributing!

## How to Contribute

### Adding a Resource

1. Fork this repository
2. Add your resource to the appropriate section in `README.md`
3. Follow the existing format for consistency
4. Submit a pull request

### Guidelines

- Ensure the resource is related to Automatic Speech Recognition
- Provide a brief, clear description
- Check that the link is working
- Avoid duplicates — search existing entries first

### Reporting Issues

If you find broken links or inaccurate information, please open an issue.

## Automation System

This repository includes automated pipelines:

- **Daily Tracker** — Runs daily at 06:00 UTC via GitHub Actions. Fetches new papers from arXiv, models from HuggingFace, and optionally tweets. Generates a daily report in `daily/`.
- **Podcast Generator** — Runs daily at 08:00 UTC. Generates a podcast script with Gemini and audio with TTS. Episodes are uploaded as GitHub Releases.
- **Mindmap Generator** — Runs weekly on Sundays. Updates the ASR topic taxonomy and renders interactive mindmaps in `mindmaps/`.
- **Email Sender** — Sends daily reports to subscribers via self-hosted SMTP.
- **Website** — Flask app serving daily reports, podcasts, and mindmaps. Deploy with `docker-compose up`.

### Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install
cp .env.example .env  # Fill in your API keys
```

Run individual modules:

```bash
python -m scripts.tracking.aggregator      # Daily tracker
python -m scripts.podcast.script_generator  # Podcast script
python -m scripts.podcast.tts_engine        # Podcast audio (needs GPU)
python -m scripts.mindmap.taxonomy_builder  # Mindmap markdown
python -m scripts.mindmap.markmap_renderer  # Mindmap HTML
python -m web.app                           # Website on :5000
```
