import re
from pathlib import Path

from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, TextClip


VIDEO_OUTPUT_DIR = Path("outputs/videos")

VIDEO_SIZE = (1080, 1920)
BACKGROUND_COLOR = (12, 12, 18)
VIDEO_FPS = 24


def _safe_filename(name):
    safe_name = name.lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "video"


def build_video(audio_path, title, output_name):
    """
    Build a simple vertical MP4 video from a voiceover audio file.

    Args:
        audio_path: Path to the generated MP3 voiceover.
        title: Text to display on the video.
        output_name: Human-readable name used for the output filename.

    Returns:
        The saved MP4 file path as a string.
    """
    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    if not title or not title.strip():
        raise ValueError("Video title is empty")

    VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = VIDEO_OUTPUT_DIR / f"{_safe_filename(output_name)}.mp4"

    audio_clip = AudioFileClip(str(audio_file))
    duration = audio_clip.duration

    background_clip = ColorClip(
        size=VIDEO_SIZE,
        color=BACKGROUND_COLOR,
        duration=duration,
    )

    title_clip = TextClip(
        text=title,
        font_size=72,
        color="white",
        method="caption",
        size=(920, None),
        text_align="center",
        duration=duration,
    ).with_position(("center", "center"))

    subtitle_clip = TextClip(
        text="RelayWorks AI Content Brain",
        font_size=34,
        color="white",
        method="caption",
        size=(900, None),
        text_align="center",
        duration=duration,
    ).with_position(("center", 1540))

    video_clip = CompositeVideoClip(
        [background_clip, title_clip, subtitle_clip],
        size=VIDEO_SIZE,
    ).with_audio(audio_clip)

    video_clip.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
    )

    video_clip.close()
    audio_clip.close()
    background_clip.close()
    title_clip.close()
    subtitle_clip.close()

    return str(output_path)
