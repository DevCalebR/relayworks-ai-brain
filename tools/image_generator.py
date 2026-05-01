import base64
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


IMAGES_OUTPUT_DIR = Path("outputs/images")
DEFAULT_IMAGE_MODEL = "gpt-image-1.5"


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


def split_script_into_image_scenes(text, image_count=5):
    """
    Split narration text into a small number of scene chunks for image prompts.
    """
    if image_count <= 0:
        raise ValueError("--image-count must be greater than 0")

    sentences = _split_sentences(text)

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


def _build_image_prompt(topic, scene_text, template):
    return (
        "Create a cinematic, moody, high-contrast YouTube Shorts background image "
        "for a weird history, mystery, or scary factual story.\n"
        f"Topic: {topic}\n"
        f"Scene: {scene_text}\n"
        f"Visual direction: historically inspired when relevant, mysterious, atmospheric, "
        f"template mood {template}, engaging but not cluttered, strong depth, dramatic "
        "lighting, vertical-friendly composition that crops well to 9:16.\n"
        "Constraints: no text, no subtitles, no captions, no logos, no watermark, "
        "no UI labels, no typography in the image, no graphic gore, no real person "
        "depicted as a specific historical figure unless the scene is generic."
    )


def generate_scene_images(
    topic,
    narration_text,
    output_name,
    image_count=5,
    template="default",
):
    """
    Generate local scene images with OpenAI and return saved PNG paths.
    """
    scenes = split_script_into_image_scenes(narration_text, image_count=image_count)

    if not scenes:
        raise ValueError("Narration text is empty; cannot generate scene images.")

    client = _get_client()
    IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    slug = _safe_filename(output_name)

    for index, scene in enumerate(scenes, start=1):
        response = client.images.generate(
            model=DEFAULT_IMAGE_MODEL,
            prompt=_build_image_prompt(topic, scene, template),
            size="1024x1536",
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
