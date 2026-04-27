import re
from pathlib import Path

import numpy as np
from moviepy import AudioClip


AUDIO_OUTPUT_DIR = Path("outputs/audio")
TEST_AUDIO_FPS = 44100
TEST_TONE_HZ = 440


def _safe_filename(name):
    safe_name = str(name).lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "test-audio"


def create_test_audio(output_name, duration_seconds=3):
    """
    Create a short local MP3 file for testing video generation.

    Args:
        output_name: Human-readable name used to create the output filename.
        duration_seconds: Length of the generated test audio.

    Returns:
        The saved MP3 file path as a string.
    """
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than 0")

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = AUDIO_OUTPUT_DIR / f"{_safe_filename(output_name)}-test.mp3"

    def make_frame(t):
        return 0.2 * np.sin(2 * np.pi * TEST_TONE_HZ * t)

    audio_clip = AudioClip(
        make_frame,
        duration=duration_seconds,
        fps=TEST_AUDIO_FPS,
    )

    audio_clip.write_audiofile(
        str(output_path),
        fps=TEST_AUDIO_FPS,
        codec="libmp3lame",
        bitrate="128k",
        logger=None,
    )
    audio_clip.close()

    return str(output_path)
