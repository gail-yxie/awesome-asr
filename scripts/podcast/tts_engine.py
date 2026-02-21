"""Text-to-speech engine for podcast audio generation.

Supports two backends:
  - "gemini" (default): Gemini 2.5 Flash TTS via Google GenAI API
  - "local": Qwen3-TTS 0.6B running locally
"""

import logging
import struct
import wave
from pathlib import Path

from scripts.config import config
from scripts.utils import PODCASTS_DIR, day_tag, read_text, set_date_override

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000


# ---------------------------------------------------------------------------
# Gemini TTS backend
# ---------------------------------------------------------------------------

def _gemini_tts_chunk(client, text: str) -> bytes:
    """Synthesize one chunk of text via Gemini TTS, return raw PCM bytes."""
    from google.genai import types

    response = client.models.generate_content(
        model=config.gemini_tts_model,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker="Host",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=config.tts_host_voice,
                                ),
                            ),
                        ),
                        types.SpeakerVoiceConfig(
                            speaker="Guest",
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=config.tts_guest_voice,
                                ),
                            ),
                        ),
                    ]
                )
            ),
        ),
    )

    if not response.candidates or not response.candidates[0].content:
        raise RuntimeError("Gemini TTS returned empty response (500/overloaded)")

    data = response.candidates[0].content.parts[0].inline_data.data
    return data


def _split_script_for_gemini(text: str, max_chars: int = 1500) -> list[str]:
    """Split script into chunks that fit the Gemini TTS input limit.

    Splits on blank lines (dialogue turn boundaries) to keep speaker
    labels intact within each chunk.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())

    return chunks


def _write_wav(pcm_data: bytes, path: Path) -> None:
    """Write raw PCM bytes (16-bit LE mono 24kHz) to a WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)


def generate_audio_gemini(script_text: str, output_stem: str | None = None) -> Path | None:
    """Generate podcast audio using Gemini 2.5 Flash TTS.

    Args:
        script_text: The podcast script text.
        output_stem: Base name for output files. Defaults to day_tag().
    """
    from google import genai

    client = genai.Client(
        api_key=config.gemini_api_key,
        http_options={
            "base_url": "https://generativelanguage.googleapis.com",
            "timeout": 120_000,  # 120s per request — TTS can be slow for long chunks
        },
    )

    chunks = _split_script_for_gemini(script_text)
    logger.info("Synthesizing %d chunk(s) via Gemini TTS...", len(chunks))

    all_pcm = bytearray()
    for i, chunk in enumerate(chunks):
        logger.info(
            "Synthesizing chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk)
        )
        pcm = _gemini_tts_chunk(client, chunk)
        all_pcm.extend(pcm)

    if not all_pcm:
        logger.error("No audio generated from Gemini TTS")
        return None

    stem = output_stem or day_tag()
    wav_path = PODCASTS_DIR / f"{stem}.wav"
    mp3_path = PODCASTS_DIR / f"{stem}.mp3"

    _write_wav(bytes(all_pcm), wav_path)
    logger.info("WAV written to %s", wav_path)

    # Convert to MP3
    from pydub import AudioSegment

    audio_segment = AudioSegment.from_wav(str(wav_path))
    audio_segment.export(str(mp3_path), format="mp3", bitrate="128k")
    logger.info("MP3 written to %s", mp3_path)

    wav_path.unlink()

    duration_min = len(audio_segment) / 1000 / 60
    logger.info("Podcast audio: %.1f minutes", duration_min)
    return mp3_path


# ---------------------------------------------------------------------------
# Local Qwen3-TTS backend
# ---------------------------------------------------------------------------

def _load_local_model():
    """Load Qwen3-TTS model and processor from HuggingFace."""
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    logger.info("Loading Qwen3-TTS model: %s", config.tts_model)
    processor = AutoProcessor.from_pretrained(
        config.tts_model,
        trust_remote_code=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        config.tts_model,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    return model, processor


def _split_into_chunks(text: str, max_chars: int = 500) -> list[str]:
    """Split text into chunks at sentence boundaries for stable TTS generation."""
    sentences = []
    for part in text.replace("\n", " ").split(". "):
        part = part.strip()
        if part:
            sentences.append(part + ".")

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = current + " " + sentence if current else sentence
    if current.strip():
        chunks.append(current.strip())

    return chunks


def generate_audio_local(script_text: str, output_stem: str | None = None) -> Path | None:
    """Generate podcast audio using local Qwen3-TTS model.

    Args:
        script_text: The podcast script text.
        output_stem: Base name for output files. Defaults to day_tag().
    """
    import numpy as np
    import torch

    model, processor = _load_local_model()

    # Strip speaker labels for single-speaker local model
    clean_text = "\n".join(
        line.split(":", 1)[1].strip() if line.startswith(("Host:", "Guest:")) else line
        for line in script_text.split("\n")
    )

    chunks = _split_into_chunks(clean_text)
    logger.info("Synthesizing %d text chunks via local Qwen3-TTS...", len(chunks))

    all_audio = []
    sample_rate = SAMPLE_RATE

    for i, chunk in enumerate(chunks):
        logger.info("Synthesizing chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))

        messages = [
            {
                "role": "user",
                "content": f"[Voice: {config.tts_voice_prompt}]\n\n{chunk}",
            }
        ]

        inputs = processor(messages, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=4096)

        audio = processor.decode(outputs[0], skip_special_tokens=True)
        if isinstance(audio, dict) and "audio" in audio:
            all_audio.append(audio["audio"])
            sample_rate = audio.get("sampling_rate", sample_rate)
        elif isinstance(audio, np.ndarray):
            all_audio.append(audio)
        else:
            logger.warning("Unexpected output format for chunk %d", i + 1)

    if not all_audio:
        logger.error("No audio generated")
        return None

    full_audio = np.concatenate(all_audio)

    stem = output_stem or day_tag()
    wav_path = PODCASTS_DIR / f"{stem}.wav"
    mp3_path = PODCASTS_DIR / f"{stem}.mp3"

    import soundfile as sf

    sf.write(str(wav_path), full_audio, sample_rate)
    logger.info("WAV written to %s", wav_path)

    from pydub import AudioSegment

    audio_segment = AudioSegment.from_wav(str(wav_path))
    audio_segment.export(str(mp3_path), format="mp3", bitrate="128k")
    logger.info("MP3 written to %s", mp3_path)

    wav_path.unlink()

    duration_min = len(audio_segment) / 1000 / 60
    logger.info("Podcast audio: %.1f minutes", duration_min)
    return mp3_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_audio(script_text: str | None = None, output_stem: str | None = None) -> Path | None:
    """Generate podcast audio from a script.

    Uses the backend configured by TTS_BACKEND (default: "gemini").

    Args:
        script_text: The podcast script text. If None, reads the latest script file.
        output_stem: Base name for output files. Defaults to day_tag().

    Returns:
        Path to the generated MP3 file, or None on failure.
    """
    dt = day_tag()

    if script_text is None:
        script_path = PODCASTS_DIR / f"{dt}-script.md"
        if not script_path.exists():
            logger.error("No script found at %s", script_path)
            return None
        raw = read_text(script_path)
        lines = raw.split("\n")
        script_text = "\n".join(
            line for line in lines if not line.startswith("# ")
        ).strip()

    if not script_text:
        logger.error("Empty script — nothing to synthesize")
        return None

    backend = config.tts_backend.lower()
    logger.info("Using TTS backend: %s", backend)

    if backend == "gemini":
        return generate_audio_gemini(script_text, output_stem=output_stem)
    elif backend == "local":
        return generate_audio_local(script_text, output_stem=output_stem)
    else:
        logger.error("Unknown TTS backend: %s (use 'gemini' or 'local')", backend)
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Generate for a specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.date:
        set_date_override(args.date)

    logging.basicConfig(level=logging.INFO)
    result = generate_audio()
    if result:
        print(f"Audio generated: {result}")
    else:
        print("Audio generation failed")
