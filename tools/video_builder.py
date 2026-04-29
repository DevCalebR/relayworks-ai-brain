import re
from pathlib import Path

from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, TextClip


VIDEO_OUTPUT_DIR = Path("outputs/videos")

VIDEO_SIZE = (1080, 1920)
VIDEO_FPS = 24
VALID_TEMPLATES = ("default", "bold", "minimal", "ai")


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


def _get_template_config(template):
    configs = {
        "default": {
            "background_color": (12, 12, 18),
            "title_font_size": 72,
            "title_color": "white",
            "title_stroke_color": None,
            "title_stroke_width": 0,
            "title_y": "center",
            "subtitle_text": "RelayWorks AI Content Brain",
            "subtitle_font_size": 34,
            "subtitle_color": "white",
            "subtitle_y": 1540,
            "caption_font_size": 58,
            "caption_color": "white",
            "caption_stroke_color": "black",
            "caption_stroke_width": 2,
            "caption_y": 1240,
            "caption_width": 900,
            "caption_box_color": (0, 0, 0),
            "caption_box_opacity": 0.58,
            "caption_padding": 34,
            "shapes": [],
        },
        "bold": {
            "background_color": (8, 8, 10),
            "title_font_size": 82,
            "title_color": "white",
            "title_stroke_color": "black",
            "title_stroke_width": 3,
            "title_y": 520,
            "subtitle_text": "RelayWorks AI Content Brain",
            "subtitle_font_size": 36,
            "subtitle_color": "#ffdd33",
            "subtitle_y": 1485,
            "caption_font_size": 64,
            "caption_color": "white",
            "caption_stroke_color": "black",
            "caption_stroke_width": 3,
            "caption_y": 1180,
            "caption_width": 880,
            "caption_box_color": (255, 43, 43),
            "caption_box_opacity": 0.86,
            "caption_padding": 38,
            "shapes": [
                {"size": (1080, 130), "color": (255, 43, 43), "opacity": 1.0, "position": (0, 0)},
                {"size": (1080, 18), "color": (255, 221, 51), "opacity": 1.0, "position": (0, 130)},
                {"size": (1080, 110), "color": (255, 43, 43), "opacity": 1.0, "position": (0, 1810)},
            ],
        },
        "minimal": {
            "background_color": (246, 247, 242),
            "title_font_size": 70,
            "title_color": "#111111",
            "title_stroke_color": None,
            "title_stroke_width": 0,
            "title_y": 610,
            "subtitle_text": "RelayWorks AI Content Brain",
            "subtitle_font_size": 30,
            "subtitle_color": "#4f5b57",
            "subtitle_y": 1450,
            "caption_font_size": 54,
            "caption_color": "#111111",
            "caption_stroke_color": None,
            "caption_stroke_width": 0,
            "caption_y": 1185,
            "caption_width": 860,
            "caption_box_color": (255, 255, 255),
            "caption_box_opacity": 0.82,
            "caption_padding": 34,
            "shapes": [
                {"size": (780, 3), "color": (34, 34, 34), "opacity": 0.22, "position": ("center", 500)},
                {"size": (780, 3), "color": (34, 34, 34), "opacity": 0.22, "position": ("center", 1395)},
            ],
        },
        "ai": {
            "background_color": (5, 11, 24),
            "title_font_size": 76,
            "title_color": "#e7fbff",
            "title_stroke_color": "#07111f",
            "title_stroke_width": 2,
            "title_y": 560,
            "subtitle_text": "RelayWorks AI Content Brain",
            "subtitle_font_size": 34,
            "subtitle_color": "#76f7d1",
            "subtitle_y": 1485,
            "caption_font_size": 58,
            "caption_color": "#f8ffff",
            "caption_stroke_color": "#06101b",
            "caption_stroke_width": 2,
            "caption_y": 1190,
            "caption_width": 880,
            "caption_box_color": (10, 28, 52),
            "caption_box_opacity": 0.84,
            "caption_padding": 36,
            "shapes": [
                {"size": (1080, 8), "color": (118, 247, 209), "opacity": 0.65, "position": (0, 220)},
                {"size": (1080, 8), "color": (84, 131, 255), "opacity": 0.65, "position": (0, 1690)},
                {"size": (8, 1420), "color": (118, 247, 209), "opacity": 0.35, "position": (128, 250)},
                {"size": (8, 1420), "color": (84, 131, 255), "opacity": 0.35, "position": (944, 250)},
                {"size": (320, 320), "color": (84, 131, 255), "opacity": 0.18, "position": (760, 120)},
                {"size": (360, 360), "color": (118, 247, 209), "opacity": 0.12, "position": (-140, 1410)},
            ],
        },
    }

    if template not in configs:
        valid_templates = ", ".join(VALID_TEMPLATES)
        raise ValueError(
            f"Unknown video template: {template}. Valid templates: {valid_templates}"
        )

    return configs[template]


def _create_background_clip(template_config, duration):
    clips = [
        ColorClip(
            size=VIDEO_SIZE,
            color=template_config["background_color"],
            duration=duration,
        )
    ]

    for shape in template_config["shapes"]:
        clip = ColorClip(
            size=shape["size"],
            color=shape["color"],
            duration=duration,
        ).with_position(shape["position"])

        if shape["opacity"] < 1:
            clip = clip.with_opacity(shape["opacity"])

        clips.append(clip)

    return CompositeVideoClip(clips, size=VIDEO_SIZE)


def _create_title_clip(title, template_config, duration):
    title_clip = TextClip(
        text=title,
        font_size=template_config["title_font_size"],
        color=template_config["title_color"],
        stroke_color=template_config["title_stroke_color"],
        stroke_width=template_config["title_stroke_width"],
        method="caption",
        size=(900, None),
        text_align="center",
        duration=duration,
    ).with_position(("center", template_config["title_y"]))

    subtitle_clip = TextClip(
        text=template_config["subtitle_text"],
        font_size=template_config["subtitle_font_size"],
        color=template_config["subtitle_color"],
        method="caption",
        size=(900, None),
        text_align="center",
        duration=duration,
    ).with_position(("center", template_config["subtitle_y"]))

    return [title_clip, subtitle_clip]


def _create_caption_clips(captions_path, template_config, max_duration):
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
                font_size=template_config["caption_font_size"],
                color=template_config["caption_color"],
                stroke_color=template_config["caption_stroke_color"],
                stroke_width=template_config["caption_stroke_width"],
                method="caption",
                size=(template_config["caption_width"], None),
                text_align="center",
                duration=caption_duration,
            )
            .with_start(caption["start"])
        )

        box_width = min(
            VIDEO_SIZE[0] - 120,
            caption_clip.w + template_config["caption_padding"] * 2,
        )
        box_height = caption_clip.h + template_config["caption_padding"] * 2
        box_y = template_config["caption_y"] - template_config["caption_padding"]

        caption_box = (
            ColorClip(
                size=(box_width, box_height),
                color=template_config["caption_box_color"],
                duration=caption_duration,
            )
            .with_opacity(template_config["caption_box_opacity"])
            .with_start(caption["start"])
            .with_position(("center", box_y))
        )

        caption_clip = caption_clip.with_position(
            ("center", template_config["caption_y"])
        )
        caption_clips.extend([caption_box, caption_clip])

    return caption_clips


def build_video(audio_path, title, output_name, captions_path=None, template="default"):
    """
    Build a simple vertical MP4 video from a voiceover audio file.

    Args:
        audio_path: Path to the generated MP3 voiceover.
        title: Text to display on the video.
        output_name: Human-readable name used for the output filename.
        captions_path: Optional SRT captions file to burn into the video.
        template: Built-in visual template name.

    Returns:
        The saved MP4 file path as a string.
    """
    template_config = _get_template_config(template)
    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    if not title or not title.strip():
        raise ValueError("Video title is empty")

    VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = VIDEO_OUTPUT_DIR / f"{_safe_filename(output_name)}.mp4"

    audio_clip = AudioFileClip(str(audio_file))
    duration = audio_clip.duration

    background_clip = _create_background_clip(template_config, duration)
    title_clips = _create_title_clip(title, template_config, duration)

    caption_clips = (
        _create_caption_clips(captions_path, template_config, duration)
        if captions_path
        else []
    )

    video_clip = CompositeVideoClip(
        [background_clip, *title_clips, *caption_clips],
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

    for title_clip in title_clips:
        title_clip.close()

    for caption_clip in caption_clips:
        caption_clip.close()

    return str(output_path)
