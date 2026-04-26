import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

AUDIO_OUTPUT_DIR = Path("outputs/audio")

# Default ElevenLabs public/sample voice.
# You can replace this later with a custom voice ID from your ElevenLabs account.
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


def _safe_filename(name):
    safe_name = name.lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "voiceover"


def generate_voiceover(text, output_name):
    """
    Generate an ElevenLabs voiceover MP3 from text.

    Args:
        text: The script text to convert into speech.
        output_name: A human-readable name used to create the output filename.

    Returns:
        The saved MP3 file path as a string.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set")

    if not text or not text.strip():
        raise ValueError("Voiceover text is empty")

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{_safe_filename(output_name)}.mp3"
    output_path = AUDIO_OUTPUT_DIR / filename

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}"
        f"?output_format={DEFAULT_OUTPUT_FORMAT}"
    )

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": DEFAULT_MODEL_ID,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.25,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            "ElevenLabs voiceover generation failed: "
            f"{response.status_code} {response.text}"
        )

    output_path.write_bytes(response.content)

    return str(output_path)
