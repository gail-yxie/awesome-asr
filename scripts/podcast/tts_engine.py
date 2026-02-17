"""Text-to-speech engine using Qwen3-TTS 0.6B for podcast audio generation."""

import logging
import os
import tempfile
from pathlib import Path

from scripts.config import config
from scripts.utils import PODCASTS_DIR, read_text, week_tag

logger = logging.getLogger(__name__)


def _load_model():
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

    chunks = []
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


def generate_audio(script_text: str | None = None) -> Path | None:
    """Generate podcast audio from a script using Qwen3-TTS.

    Args:
        script_text: The podcast script text. If None, reads the latest script file.

    Returns:
        Path to the generated MP3 file, or None on failure.
    """
    wt = week_tag()

    if script_text is None:
        script_path = PODCASTS_DIR / f"{wt}-script.md"
        if not script_path.exists():
            logger.error("No script found at %s", script_path)
            return None
        raw = read_text(script_path)
        # Strip the markdown header
        lines = raw.split("\n")
        script_text = "\n".join(
            line for line in lines if not line.startswith("# ")
        ).strip()

    if not script_text:
        logger.error("Empty script — nothing to synthesize")
        return None

    import torch
    import numpy as np

    model, processor = _load_model()

    chunks = _split_into_chunks(script_text)
    logger.info("Synthesizing %d text chunks...", len(chunks))

    all_audio = []
    sample_rate = 24000

    for i, chunk in enumerate(chunks):
        logger.info("Synthesizing chunk %d/%d (%d chars)", i + 1, len(chunks), len(chunk))

        # Prepare input with voice design prompt
        messages = [
            {
                "role": "user",
                "content": (
                    f"[Voice: {config.tts_voice_prompt}]\n\n{chunk}"
                ),
            }
        ]

        inputs = processor(
            messages,
            return_tensors="pt",
        ).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=4096,
            )

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

    # Concatenate all audio chunks
    full_audio = np.concatenate(all_audio)

    # Save as WAV then convert to MP3
    wav_path = PODCASTS_DIR / f"{wt}.wav"
    mp3_path = PODCASTS_DIR / f"{wt}.mp3"

    import soundfile as sf

    sf.write(str(wav_path), full_audio, sample_rate)
    logger.info("WAV written to %s", wav_path)

    # Convert to MP3 using pydub (requires ffmpeg)
    from pydub import AudioSegment

    audio_segment = AudioSegment.from_wav(str(wav_path))
    audio_segment.export(str(mp3_path), format="mp3", bitrate="128k")
    logger.info("MP3 written to %s", mp3_path)

    # Clean up WAV
    wav_path.unlink()

    duration_min = len(audio_segment) / 1000 / 60
    logger.info("Podcast audio: %.1f minutes", duration_min)

    return mp3_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = generate_audio()
    if result:
        print(f"Audio generated: {result}")
    else:
        print("Audio generation failed")
