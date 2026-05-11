import re
from pathlib import Path

from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, ImageClip, TextClip


VIDEO_OUTPUT_DIR = Path("outputs/videos")

VIDEO_FORMATS = {
    "vertical": (1080, 1920),
    "landscape": (1920, 1080),
}
VIDEO_FPS = 24
TITLE_DISPLAY_SECONDS = 4
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


def _get_video_size(video_format):
    if video_format not in VIDEO_FORMATS:
        valid_formats = ", ".join(VIDEO_FORMATS)
        raise ValueError(
            f"Unknown video format: {video_format}. Valid formats: {valid_formats}"
        )

    return VIDEO_FORMATS[video_format]


def _get_template_config(template, video_format="vertical"):
    configs = {
        "default": {
            "background_color": (12, 12, 18),
            "title_font_size": 72,
            "title_color": "white",
            "title_stroke_color": None,
            "title_stroke_width": 0,
            "title_y": "center",
            "caption_font_size": 58,
            "caption_color": "white",
            "caption_stroke_color": "black",
            "caption_stroke_width": 2,
            "caption_y": 1240,
            "caption_width": 900,
            "caption_box_color": (0, 0, 0),
            "caption_box_opacity": 0.58,
            "caption_padding": 34,
        },
        "bold": {
            "background_color": (8, 8, 10),
            "title_font_size": 82,
            "title_color": "white",
            "title_stroke_color": "black",
            "title_stroke_width": 3,
            "title_y": 520,
            "caption_font_size": 64,
            "caption_color": "white",
            "caption_stroke_color": "black",
            "caption_stroke_width": 3,
            "caption_y": 1180,
            "caption_width": 880,
            "caption_box_color": (255, 43, 43),
            "caption_box_opacity": 0.86,
            "caption_padding": 38,
        },
        "minimal": {
            "background_color": (246, 247, 242),
            "title_font_size": 70,
            "title_color": "#111111",
            "title_stroke_color": None,
            "title_stroke_width": 0,
            "title_y": 610,
            "caption_font_size": 54,
            "caption_color": "#111111",
            "caption_stroke_color": None,
            "caption_stroke_width": 0,
            "caption_y": 1185,
            "caption_width": 860,
            "caption_box_color": (255, 255, 255),
            "caption_box_opacity": 0.82,
            "caption_padding": 34,
        },
        "ai": {
            "background_color": (5, 11, 24),
            "title_font_size": 76,
            "title_color": "#e7fbff",
            "title_stroke_color": "#07111f",
            "title_stroke_width": 2,
            "title_y": 560,
            "caption_font_size": 58,
            "caption_color": "#f8ffff",
            "caption_stroke_color": "#06101b",
            "caption_stroke_width": 2,
            "caption_y": 1190,
            "caption_width": 880,
            "caption_box_color": (10, 28, 52),
            "caption_box_opacity": 0.84,
            "caption_padding": 36,
        },
    }

    if template not in configs:
        valid_templates = ", ".join(VALID_TEMPLATES)
        raise ValueError(
            f"Unknown video template: {template}. Valid templates: {valid_templates}"
        )

    config = dict(configs[template])

    if video_format == "vertical":
        return config

    _get_video_size(video_format)

    font_scale = 0.78

    config["title_font_size"] = int(config["title_font_size"] * font_scale)
    config["caption_font_size"] = int(config["caption_font_size"] * font_scale)
    config["title_y"] = int(270 if template != "bold" else 230)
    config["caption_y"] = 780
    config["caption_width"] = 1320
    config["caption_padding"] = int(config["caption_padding"] * 0.78)

    return config


def _create_background_clip(template_config, duration, video_size):
    return ColorClip(
        size=video_size,
        color=template_config["background_color"],
        duration=duration,
    )


def _create_cover_image_clip(image_path, duration, video_size, start_time=0):
    image_file = Path(image_path)

    if not image_file.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_path}")

    image_clip = ImageClip(str(image_file), duration=duration)
    image_width, image_height = image_clip.size
    video_width, video_height = video_size
    scale = max(video_width / image_width, video_height / image_height)
    resized_clip = image_clip.resized(
        new_size=(int(image_width * scale), int(image_height * scale))
    )
    cropped_clip = resized_clip.cropped(
        x_center=resized_clip.w / 2,
        y_center=resized_clip.h / 2,
        width=video_width,
        height=video_height,
    )

    if start_time:
        cropped_clip = cropped_clip.with_start(start_time)

    return cropped_clip


def _create_image_background_clip(image_paths, template_config, duration, video_size):
    if not image_paths:
        raise ValueError("image_paths must contain at least one image")

    if len(image_paths) == 1:
        return _create_cover_image_clip(image_paths[0], duration, video_size)

    clips = []
    image_duration = duration / len(image_paths)

    for index, image_path in enumerate(image_paths):
        start_time = index * image_duration
        clip_duration = (
            duration - start_time
            if index == len(image_paths) - 1
            else image_duration
        )
        clips.append(
            _create_cover_image_clip(
                image_path,
                clip_duration,
                video_size,
                start_time,
            )
        )

    return CompositeVideoClip(clips, size=video_size)


def _create_title_clip(title, template_config, duration, video_size):
    title_duration = min(TITLE_DISPLAY_SECONDS, duration)

    title_clip = TextClip(
        text=title,
        font_size=template_config["title_font_size"],
        color=template_config["title_color"],
        stroke_color=template_config["title_stroke_color"],
        stroke_width=template_config["title_stroke_width"],
        method="caption",
        size=(min(video_size[0] - 220, 1320), None),
        text_align="center",
        duration=title_duration,
    ).with_position(("center", template_config["title_y"]))

    return [title_clip]


def _create_caption_clips(captions_path, template_config, max_duration, video_size):
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
            video_size[0] - 120,
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


def build_video(
    audio_path,
    title,
    output_name,
    captions_path=None,
    template="default",
    image_paths=None,
    video_format="vertical",
):
    """
    Build a simple MP4 video from a voiceover audio file.

    Args:
        audio_path: Path to the generated MP3 voiceover.
        title: Text to display on the video.
        output_name: Human-readable name used for the output filename.
        captions_path: Optional SRT captions file to burn into the video.
        template: Built-in visual template name.
        image_paths: Optional local image paths to use as the main visual layer.
        video_format: Output aspect format. Valid values: vertical, landscape.

    Returns:
        The saved MP4 file path as a string.
    """
    video_size = _get_video_size(video_format)
    template_config = _get_template_config(template, video_format)
    audio_file = Path(audio_path)

    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    if not title or not title.strip():
        raise ValueError("Video title is empty")

    VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = VIDEO_OUTPUT_DIR / f"{_safe_filename(output_name)}.mp4"

    audio_clip = AudioFileClip(str(audio_file))
    duration = audio_clip.duration

    background_clip = (
        _create_image_background_clip(
            image_paths,
            template_config,
            duration,
            video_size,
        )
        if image_paths
        else _create_background_clip(template_config, duration, video_size)
    )
    title_clips = _create_title_clip(title, template_config, duration, video_size)

    caption_clips = (
        _create_caption_clips(captions_path, template_config, duration, video_size)
        if captions_path
        else []
    )

    video_clip = CompositeVideoClip(
        [background_clip, *title_clips, *caption_clips],
        size=video_size,
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
