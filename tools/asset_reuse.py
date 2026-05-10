import re
from pathlib import Path


SCRIPT_OUTPUT_DIR = Path("outputs/scripts")
METADATA_OUTPUT_DIR = Path("outputs/metadata")
IMAGES_OUTPUT_DIR = Path("outputs/images")
THUMBNAILS_OUTPUT_DIR = Path("outputs/thumbnails")
AUDIO_OUTPUT_DIR = Path("outputs/audio")


def get_output_slug(output_name):
    slug = str(output_name).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "asset"


def _get_script_slug(output_name):
    slug = str(output_name).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "script"


def find_existing_script_path(output_name, output_dir=SCRIPT_OUTPUT_DIR):
    output_path = Path(output_dir) / f"{_get_script_slug(output_name)}.txt"
    return output_path if output_path.is_file() else None


def find_existing_metadata_path(output_name, output_dir=METADATA_OUTPUT_DIR):
    output_path = Path(output_dir) / f"{get_output_slug(output_name)}.json"
    return output_path if output_path.is_file() else None


def expected_scene_image_paths(output_name, image_count, output_dir=IMAGES_OUTPUT_DIR):
    if image_count <= 0:
        raise ValueError("image_count must be greater than 0")

    slug = get_output_slug(output_name)
    return [
        Path(output_dir) / f"{slug}-scene-{index:02}.png"
        for index in range(1, image_count + 1)
    ]


def find_existing_scene_images(output_name, image_count, output_dir=IMAGES_OUTPUT_DIR):
    return [
        image_path
        for image_path in expected_scene_image_paths(
            output_name,
            image_count,
            output_dir,
        )
        if image_path.is_file()
    ]


def find_existing_thumbnail_path(output_name, output_dir=THUMBNAILS_OUTPUT_DIR):
    output_path = Path(output_dir) / f"{get_output_slug(output_name)}-thumbnail.png"
    return output_path if output_path.is_file() else None


def find_existing_audio_path(output_name, output_dir=AUDIO_OUTPUT_DIR):
    output_path = Path(output_dir) / f"{get_output_slug(output_name)}.mp3"
    return output_path if output_path.is_file() else None
