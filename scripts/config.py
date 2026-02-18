import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # LLM (Gemini)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    # HuggingFace
    hf_token: str = os.getenv("HF_TOKEN", "")

    # Twitter (optional)
    twitter_bearer_token: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    # TTS
    tts_backend: str = os.getenv("TTS_BACKEND", "gemini")  # "gemini" or "local"
    gemini_tts_model: str = os.getenv(
        "GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"
    )
    tts_host_voice: str = os.getenv("TTS_HOST_VOICE", "Charon")
    tts_guest_voice: str = os.getenv("TTS_GUEST_VOICE", "Puck")

    # TTS (local Qwen3-TTS fallback)
    tts_model: str = os.getenv("TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-Base")
    tts_voice_prompt: str = os.getenv(
        "TTS_VOICE_PROMPT",
        "A calm, clear, professional English-speaking podcast host voice.",
    )

    # Podcast
    podcast_target_words: int = int(os.getenv("PODCAST_TARGET_WORDS", "1800"))

    # Mindmap
    mindmap_lookback_days: int = int(os.getenv("MINDMAP_LOOKBACK_DAYS", "30"))

    # Email (SMTP)
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_address: str = os.getenv("SMTP_FROM_ADDRESS", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    # Website
    site_url: str = os.getenv("SITE_URL", "http://localhost:5000")

    @property
    def twitter_enabled(self) -> bool:
        return bool(self.twitter_bearer_token)

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_address)


config = Config()
