import base64
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


IMAGES_OUTPUT_DIR = Path("outputs/images")
DEFAULT_IMAGE_MODEL = "gpt-image-1.5"
IMAGE_SIZES = {
    "vertical": "1024x1536",
    "landscape": "1536x1024",
}


load_dotenv()


def _get_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when --use-ai-images is set.")

    return OpenAI(api_key=api_key)


def _safe_filename(name):
    safe_name = str(name).lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "image"


def _split_sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]


def _clean_scene_text(text):
    cleaned = re.sub(r"(?im)^\s*topic:\s*.*(?:\n|$)", " ", str(text))
    cleaned = re.sub(r"\[[^\]]+\]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _expand_story_units(sentences):
    expanded = []

    for sentence in sentences:
        parts = [
            part.strip()
            for part in re.split(r"(?<=[;:])\s+|(?<=\s-\s)", sentence)
            if part.strip()
        ]
        expanded.extend(parts or [sentence])

    return expanded


def split_script_into_image_scenes(text, image_count=5):
    """
    Split narration text into ordered story beats for image prompts.
    """
    if image_count <= 0:
        raise ValueError("--image-count must be greater than 0")

    sentences = [_clean_scene_text(sentence) for sentence in _split_sentences(text)]
    sentences = [sentence for sentence in sentences if sentence]
    sentences = _expand_story_units(sentences)

    if not sentences:
        return []

    scene_count = min(image_count, len(sentences))
    scenes = []

    for index in range(scene_count):
        start = round(index * len(sentences) / scene_count)
        end = round((index + 1) * len(sentences) / scene_count)
        scene = " ".join(sentences[start:end]).strip()

        if scene:
            scenes.append(scene)

    return scenes


def _image_size_for_format(video_format):
    if video_format not in IMAGE_SIZES:
        valid_formats = ", ".join(IMAGE_SIZES)
        raise ValueError(
            f"Unknown video format: {video_format}. Valid formats: {valid_formats}"
        )

    return IMAGE_SIZES[video_format]


def _format_visual_direction(video_format):
    if video_format == "landscape":
        return (
            "landscape YouTube episode composition that crops cleanly to 16:9, "
            "cinematic midground subject, readable lower-third safe area"
        )

    return "vertical-friendly composition that crops well to 9:16"


def _build_image_prompt(topic, scene_text, template, video_format="vertical"):
    return (
        "Create a cinematic, moody, high-contrast video background image for a "
        "weird history, mystery, or scary factual episode.\n"
        f"Topic: {topic}\n"
        f"Exact narration beat to visualize: {scene_text}\n"
        f"Visual direction: historically inspired when relevant, mysterious, atmospheric, "
        f"template mood {template}, engaging but not cluttered, strong depth, dramatic "
        f"lighting, {_format_visual_direction(video_format)}. Represent this specific "
        "story beat rather than the general topic.\n"
        "Constraints: no text, no subtitles, no captions, no logos, no watermark, "
        "no UI labels, no typography in the image, no graphic gore, avoid explicit "
        "violence, no real person depicted as a specific historical figure unless "
        "the scene is generic. If the beat mentions a written clue or carving, show "
        "a mysterious carved mark without relying on readable letters."
    )


def generate_scene_images(
    topic,
    narration_text,
    output_name,
    image_count=5,
    template="default",
    video_format="vertical",
):
    """
    Generate local scene images with OpenAI and return saved PNG paths.
    """
    scenes = split_script_into_image_scenes(narration_text, image_count=image_count)
    image_size = _image_size_for_format(video_format)

    if not scenes:
        raise ValueError("Narration text is empty; cannot generate scene images.")

    client = _get_client()
    IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    slug = _safe_filename(output_name)

    for index, scene in enumerate(scenes, start=1):
        response = client.images.generate(
            model=DEFAULT_IMAGE_MODEL,
            prompt=_build_image_prompt(topic, scene, template, video_format),
            size=image_size,
            quality="low",
            output_format="png",
            n=1,
        )

        image_data = response.data[0].b64_json

        if not image_data:
            raise ValueError("OpenAI image response did not include image data.")

        output_path = IMAGES_OUTPUT_DIR / f"{slug}-scene-{index:02}.png"
        output_path.write_bytes(base64.b64decode(image_data))
        saved_paths.append(str(output_path))

    return saved_paths
