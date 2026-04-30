import base64
import os
import re
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFilter, ImageFont


THUMBNAILS_OUTPUT_DIR = Path("outputs/thumbnails")
THUMBNAIL_SIZE = (1280, 720)
DEFAULT_IMAGE_MODEL = "gpt-image-1.5"


load_dotenv()


def _safe_filename(name):
    safe_name = str(name).lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "thumbnail"


def _find_font(size):
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]

    for font_path in font_paths:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)

    return ImageFont.load_default()


def _cover_resize(image, size=THUMBNAIL_SIZE):
    image = image.convert("RGB")
    source_width, source_height = image.size
    target_width, target_height = size
    scale = max(target_width / source_width, target_height / source_height)
    resized_size = (
        int(source_width * scale),
        int(source_height * scale),
    )
    image = image.resize(resized_size, Image.Resampling.LANCZOS)

    left = (image.width - target_width) // 2
    top = (image.height - target_height) // 2
    return image.crop((left, top, left + target_width, top + target_height))


def _clean_title(topic):
    title = re.sub(r"\s+", " ", str(topic)).strip()
    title = re.sub(r"[#*_`]+", "", title)
    return title[:90] or "RelayWorks AI"


def _wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    for word in words:
        candidate = f"{current_line} {word}".strip()
        bbox = measure.textbbox((0, 0), candidate, font=font)

        if bbox[2] - bbox[0] <= max_width or not current_line:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines[:3]


def _add_title_overlay(image, topic, template="ai"):
    draw = ImageDraw.Draw(image)
    width, height = image.size

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 68))
    overlay_draw.rectangle((0, height - 230, width, height), fill=(0, 0, 0, 118))
    image.alpha_composite(overlay)

    title = _clean_title(topic).upper()
    max_width = width - 160
    font_size = 86

    while font_size >= 48:
        title_font = _find_font(font_size)
        title_lines = _wrap_text(title, title_font, max_width)
        line_height = font_size + 10

        if len(title_lines) * line_height <= 285:
            break

        font_size -= 6

    brand_font = _find_font(34)
    accent_color = (70, 230, 210) if template == "ai" else (255, 210, 76)
    text_color = (255, 255, 255)
    shadow_color = (0, 0, 0)

    draw.rounded_rectangle((64, 54, 360, 110), radius=18, fill=(12, 18, 24))
    draw.text((84, 64), "RELAYWORKS AI", font=brand_font, fill=accent_color)

    y = height - (len(title_lines) * (font_size + 10)) - 64

    for line in title_lines:
        draw.text((82, y + 5), line, font=title_font, fill=shadow_color)
        draw.text((76, y), line, font=title_font, fill=text_color)
        y += font_size + 10

    draw.rectangle((76, height - 38, 500, height - 26), fill=accent_color)
    return image.convert("RGB")


def _create_local_background():
    width, height = THUMBNAIL_SIZE
    image = Image.new("RGB", THUMBNAIL_SIZE, (12, 18, 24))
    draw = ImageDraw.Draw(image)

    for x in range(width):
        ratio = x / width
        color = (
            int(12 + ratio * 22),
            int(18 + ratio * 38),
            int(24 + ratio * 58),
        )
        draw.line((x, 0, x, height), fill=color)

    for index, color in enumerate([(70, 230, 210), (255, 210, 76), (86, 130, 255)]):
        x = 760 + index * 110
        y = 130 + index * 80
        draw.ellipse((x, y, x + 360, y + 360), fill=color)

    image = image.filter(ImageFilter.GaussianBlur(radius=26))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((690, 150, 1160, 570), radius=28, outline=(255, 255, 255), width=4)
    draw.line((740, 290, 1110, 290), fill=(70, 230, 210), width=10)
    draw.line((740, 370, 1040, 370), fill=(255, 210, 76), width=10)
    draw.line((740, 450, 1090, 450), fill=(255, 255, 255), width=10)

    return image.convert("RGBA")


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when --use-ai-thumbnail is set.")

    return OpenAI(api_key=api_key)


def _generate_ai_background(topic, template):
    client = _get_openai_client()
    prompt = (
        "Create a YouTube thumbnail background image for a short-form business video.\n"
        f"Topic: {topic}\n"
        f"Style: high contrast, modern AI/business feel, template mood {template}, "
        "bold composition, clean depth, premium lighting, thumbnail-friendly landscape.\n"
        "Constraints: no small unreadable text, no subtitles, no watermark, no logos, "
        "no typography, leave room for a large local title overlay."
    )
    response = client.images.generate(
        model=DEFAULT_IMAGE_MODEL,
        prompt=prompt,
        size="1536x1024",
        quality="low",
        output_format="png",
        n=1,
    )
    image_data = response.data[0].b64_json

    if not image_data:
        raise ValueError("OpenAI thumbnail response did not include image data.")

    return Image.open(BytesIO(base64.b64decode(image_data))).convert("RGBA")


def _load_source_image(source_image_paths):
    for image_path in source_image_paths or []:
        source_path = Path(image_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Thumbnail source image does not exist: {image_path}")

        if not source_path.is_file():
            raise ValueError(f"Thumbnail source image is not a file: {image_path}")

        return Image.open(source_path).convert("RGBA")

    return None


def generate_thumbnail(
    topic,
    output_name,
    source_image_paths=None,
    use_ai=False,
    template="ai",
):
    """
    Generate a local 1280x720 YouTube thumbnail image and return its path.
    """
    THUMBNAILS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_image = _load_source_image(source_image_paths)

    if source_image is not None:
        base_image = _cover_resize(source_image).convert("RGBA")
    elif use_ai:
        base_image = _cover_resize(_generate_ai_background(topic, template)).convert("RGBA")
    else:
        base_image = _create_local_background()

    thumbnail = _add_title_overlay(base_image, topic, template=template)
    output_path = THUMBNAILS_OUTPUT_DIR / f"{_safe_filename(output_name)}-thumbnail.png"
    thumbnail.save(output_path, format="PNG")

    return str(output_path)
