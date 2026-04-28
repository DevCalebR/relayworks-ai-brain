import re
from pathlib import Path

from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, TextClip


VIDEO_OUTPUT_DIR = Path("outputs/videos")

VIDEO_SIZE = (1080, 1920)
BACKGROUND_COLOR = (12, 12, 18)
VIDEO_FPS = 24
CAPTION_FONT_SIZE = 56
CAPTION_POSITION_Y = 1260


def _safe_filename(name):
    safe_name = name.lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "video"


def _parse_srt_timestamp(timestamp):
    hours, minutes, rest = timestamp.strip().split(":")
    seconds, milliseconds = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def _parse_srt_captions(captions_path):
    captions_file = Path(captions_path)

    if not captions_file.exists():
        raise FileNotFoundError(f"Captions file does not exist: {captions_path}")

    content = captions_file.read_text(encoding="utf-8").strip()

    if not content:
        return []

    captions = []

    for block in re.split(r"\n\s*\n", content):
        lines = [line.strip() for line in block.splitlines() if line.strip()]

        if len(lines) < 3:
            continue

        timestamp_line = lines[1]

        if "-->" not in timestamp_line:
            continue

        start_timestamp, end_timestamp = [
            timestamp.strip() for timestamp in timestamp_line.split("-->", 1)
        ]
        start_time = _parse_srt_timestamp(start_timestamp)
        end_time = _parse_srt_timestamp(end_timestamp)
        text = " ".join(lines[2:])

        if end_time <= start_time or not text:
            continue

        captions.append(
            {
                "start": start_time,
                "duration": end_time - start_time,
                "text": text,
            }
        )

    return captions


def _create_caption_clips(captions_path, max_duration):
    caption_clips = []

    for caption in _parse_srt_captions(captions_path):
        if caption["start"] >= max_duration:
            continue

        caption_duration = min(
            caption["duration"],
            max_duration - caption["start"],
        )

        caption_clip = (
            TextClip(
                text=caption["text"],
                font_size=CAPTION_FONT_SIZE,
                color="white",
                method="caption",
                size=(900, None),
                text_align="center",
                duration=caption_duration,
            )
            .with_start(caption["start"])
            .with_position(("center", CAPTION_POSITION_Y))
        )
        caption_clips.append(caption_clip)

    return caption_clips


def build_video(audio_path, title, output_name, captions_path=None):
    """
    Build a simple vertical MP4 video from a voiceover audio file.

    Args:
        audio_path: Path to the generated MP3 voiceover.
        title: Text to display on the video.
        output_name: Human-readable name used for the output filename.
        captions_path: Optional SRT captions file to burn into the video.

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

    caption_clips = (
        _create_caption_clips(captions_path, duration) if captions_path else []
    )

    video_clip = CompositeVideoClip(
        [background_clip, title_clip, subtitle_clip, *caption_clips],
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

    for caption_clip in caption_clips:
        caption_clip.close()

    return str(output_path)
