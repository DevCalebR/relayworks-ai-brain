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
SAFE_IMAGE_CONSTRAINTS = (
    "Safety constraints: documentary-style historical visual, no children, "
    "no bodies, no gore, no violence, no active fire, no distress, "
    "no readable text, no watermark, no logos, no UI labels, no typography."
)
GENERIC_SAFE_FALLBACK_PROMPT = (
    "Atmospheric documentary-style image of a quiet historical town at night, "
    "foggy hills, old road, archival mystery mood, no people, no fire, "
    "no violence, no readable text, no watermark."
)
APPALACHIAN_SAFE_FALLBACK_PROMPT = (
    "Atmospheric documentary-style image of a quiet 1940s Appalachian town at "
    "night, foggy hills, old road, historical mystery mood, no people, no fire, "
    "no violence, no readable text, no watermark."
)
SENSITIVE_VISUAL_REPLACEMENTS = [
    (
        r"\b(house|home|building)\s+fires?\b|\bactive\s+fires?\b|\bburning\s+(house|home|building)\b",
        "old house exterior at night, smoke-free, calm documentary style",
    ),
    (
        r"\b(missing|vanished|disappeared|gone)\s+(children|child|kids|boys|girls|siblings)\b",
        "vintage missing-person case file on a desk, no faces",
    ),
    (
        r"\b(children|child|kids|boys|girls|siblings)\s+(were|are|was|is)?\s*(missing|vanished|disappeared|gone|in danger|trapped)\b",
        "vintage missing-person case file on a desk, no faces",
    ),
    (
        r"\b(children|child|kids|boys|girls|siblings)\b",
        "family case records",
    ),
    (
        r"\b(bodies|body|remains|bones|corpse|corpses)\b",
        "archival investigation notes and evidence markers, no people shown",
    ),
    (
        r"\b(kidnapping|kidnapped|kidnapper|abduction|abducted|abductor)\b",
        "unanswered mystery represented by an empty rural road",
    ),
    (
        r"\b(death|deaths|dead|died|dies|killed|killing|murder|murdered)\b",
        "somber historical mystery atmosphere",
    ),
    (
        r"\b(self[-\s]?harm|suicide|suicidal)\b",
        "somber historical mystery atmosphere",
    ),
    (
        r"\b(gore|gory|blood|bloody|wound|wounds)\b",
        "archival case materials, clean documentary style",
    ),
    (
        r"\b(violence|violent|attack|attacked|assault|weapon|gun|knife)\b",
        "quiet historical mystery setting",
    ),
    (
        r"\b(distress|distressed|terror|terrified|panic|screaming|crying|grief|grieving)\b",
        "somber documentary atmosphere",
    ),
    (
        r"\b(fire|flames|burning|burned|burnt|charred|smoke inhalation)\b",
        "smoke-free historical exterior, calm documentary style",
    ),
]
UNSAFE_VISUAL_PATTERNS = [
    r"\b(self[-\s]?harm|suicide|suicidal)\b",
    r"\b(gore|gory|blood|bloody|wound|wounds)\b",
    r"\b(bodies|body|remains|bones|corpse|corpses)\b",
    r"\b(death|deaths|dead|died|dies|killed|killing|murder|murdered)\b",
    r"\b(kidnapping|kidnapped|kidnapper|abduction|abducted|abductor)\b",
    r"\b(violence|violent|attack|attacked|assault|weapon|gun|knife)\b",
    r"\b(distress|distressed|terror|terrified|panic|screaming|crying|grief|grieving)\b",
    r"\b(active\s+fire|house\s+fire|home\s+fire|flames|burning|burned|burnt|charred)\b",
    r"\b(children|child|kids|boys|girls|siblings)\b.*\b(missing|vanished|disappeared|danger|trapped|kidnapped|abducted)\b",
    r"\b(missing|vanished|disappeared|danger|trapped|kidnapped|abducted)\b.*\b(children|child|kids|boys|girls|siblings)\b",
]


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


def _has_unsafe_visual_context(text):
    return any(
        re.search(pattern, str(text), flags=re.I)
        for pattern in UNSAFE_VISUAL_PATTERNS
    )


def sanitize_image_prompt_context(text, topic=None):
    """
    Convert sensitive narration into safer documentary visual context.
    """
    sanitized = _clean_scene_text(text)

    for pattern, replacement in SENSITIVE_VISUAL_REPLACEMENTS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.I)

    if topic and _has_unsafe_visual_context(sanitized):
        sanitized = _fallback_visual_context(topic)

    sanitized = re.sub(r"\s+", " ", sanitized).strip(" ,.;:-")
    return sanitized


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


def _fallback_visual_context(topic):
    topic_text = str(topic).lower()

    if any(
        keyword in topic_text
        for keyword in ("sodder", "west virginia", "fayetteville", "appalach")
    ):
        return APPALACHIAN_SAFE_FALLBACK_PROMPT

    return GENERIC_SAFE_FALLBACK_PROMPT


def _safe_topic_label(topic):
    topic_text = str(topic).lower()

    if any(
        keyword in topic_text
        for keyword in ("sodder", "west virginia", "fayetteville", "appalach")
    ):
        return "The historical Sodder family mystery in 1940s West Virginia"

    safe_topic = sanitize_image_prompt_context(topic)

    if _has_unsafe_visual_context(safe_topic):
        return "Sensitive historical mystery case"

    return safe_topic or "Historical mystery"


def _build_fallback_image_prompt(topic, template, video_format="vertical"):
    return (
        "Create a safe atmospheric documentary-style historical visual.\n"
        f"Topic context: {_safe_topic_label(topic)}\n"
        f"Visual direction: {_fallback_visual_context(topic)} "
        f"Template mood {template}, {_format_visual_direction(video_format)}.\n"
        f"{SAFE_IMAGE_CONSTRAINTS}"
    )


def _build_image_prompt(topic, scene_text, template, video_format="vertical"):
    safe_scene_text = sanitize_image_prompt_context(scene_text, topic=topic)

    if _has_unsafe_visual_context(safe_scene_text):
        return _build_fallback_image_prompt(topic, template, video_format)

    return (
        "Create a cinematic, moody, high-contrast documentary-style historical "
        "visual for a weird history, mystery, or scary factual episode.\n"
        f"Topic context: {_safe_topic_label(topic)}\n"
        f"Safe narration beat to visualize: {safe_scene_text}\n"
        f"Visual direction: historically inspired when relevant, mysterious, atmospheric, "
        f"template mood {template}, engaging but not cluttered, strong depth, dramatic "
        f"lighting, {_format_visual_direction(video_format)}. Represent this specific "
        "story beat rather than the general topic.\n"
        f"{SAFE_IMAGE_CONSTRAINTS} No real person depicted as a specific "
        "historical figure unless the scene is generic. If the beat mentions a "
        "written clue or carving, show a mysterious carved mark without relying "
        "on readable letters."
    )


def _is_moderation_blocked_error(error):
    details = " ".join(
        str(value)
        for value in (
            type(error).__name__,
            getattr(error, "code", ""),
            getattr(error, "type", ""),
            getattr(error, "message", ""),
            str(error),
        )
    )
    details = details.lower()
    return "moderation_blocked" in details or "safety" in details


def _request_image(client, prompt, image_size):
    return client.images.generate(
        model=DEFAULT_IMAGE_MODEL,
        prompt=prompt,
        size=image_size,
        quality="low",
        output_format="png",
        n=1,
    )


def generate_scene_images(
    topic,
    narration_text,
    output_name,
    image_count=5,
    template="default",
    video_format="vertical",
    skip_existing=False,
):
    """
    Generate local scene images with OpenAI and return saved PNG paths.
    """
    scenes = split_script_into_image_scenes(narration_text, image_count=image_count)
    image_size = _image_size_for_format(video_format)

    if not scenes:
        raise ValueError("Narration text is empty; cannot generate scene images.")

    IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = None
    saved_paths = []
    slug = _safe_filename(output_name)

    for index, scene in enumerate(scenes, start=1):
        output_path = IMAGES_OUTPUT_DIR / f"{slug}-scene-{index:02}.png"

        if skip_existing and output_path.is_file():
            saved_paths.append(str(output_path))
            continue

        if client is None:
            client = _get_client()

        prompt = _build_image_prompt(topic, scene, template, video_format)

        try:
            response = _request_image(client, prompt, image_size)
        except Exception as exc:
            if not _is_moderation_blocked_error(exc):
                raise

            fallback_prompt = _build_fallback_image_prompt(
                topic,
                template,
                video_format,
            )

            try:
                response = _request_image(client, fallback_prompt, image_size)
            except Exception as fallback_exc:
                raise RuntimeError(
                    "OpenAI image generation failed safety moderation for "
                    f"scene {index}, and the safer fallback prompt also failed."
                ) from fallback_exc

        image_data = response.data[0].b64_json

        if not image_data:
            raise ValueError(
                f"OpenAI image response did not include image data for scene {index}."
            )

        output_path.write_bytes(base64.b64decode(image_data))
        saved_paths.append(str(output_path))

    return saved_paths
