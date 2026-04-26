import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

OUTPUTS_DIR = Path("outputs/audio")
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
TTS_URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def _safe_filename(output_name: str) -> str:
    slug = output_name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "voiceover"


def generate_voiceover(text: str, output_name: str) -> str:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS_DIR / f"{_safe_filename(output_name)}.mp3"

    response = requests.post(
        TTS_URL_TEMPLATE.format(voice_id=DEFAULT_VOICE_ID),
        params={"output_format": "mp3_44100_128"},
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        },
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
        },
        timeout=120,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        message = (
            f"ElevenLabs voiceover request failed with status "
            f"{response.status_code}: {response.text}"
        )
        raise RuntimeError(message) from exc

    output_path.write_bytes(response.content)
    return str(output_path)
