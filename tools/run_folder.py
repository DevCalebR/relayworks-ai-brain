import re
import shutil
from datetime import datetime
from pathlib import Path


RUNS_OUTPUT_DIR = Path("outputs/runs")
OUTPUT_FILENAMES = {
    "script": "script.txt",
    "captions": "captions.srt",
    "metadata": "metadata.json",
    "audio": "audio.mp3",
    "video": "video.mp4",
    "thumbnail": "thumbnail.png",
}


def _safe_topic_slug(topic):
    slug = str(topic).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "run"


def organize_run_outputs(topic, outputs):
    """
    Copy generated pipeline outputs into a timestamped local run folder.

    Args:
        topic: Pipeline topic used to name the run folder.
        outputs: Dictionary of generated output paths.

    Returns:
        A dictionary with the run folder path and copied output paths.
    """
    RUNS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_folder = RUNS_OUTPUT_DIR / f"{_safe_topic_slug(topic)}-{timestamp}"
    run_folder.mkdir(parents=True, exist_ok=True)

    copied_outputs = copy_outputs_to_run_folder(outputs, run_folder)

    return {
        "run_folder": str(run_folder),
        "copied_outputs": copied_outputs,
    }


def copy_outputs_to_run_folder(outputs, run_folder):
    """
    Copy generated pipeline outputs into a specific local run folder.

    Args:
        outputs: Dictionary of generated output paths.
        run_folder: Destination folder that should receive upload-ready files.

    Returns:
        A dictionary of copied output paths.
    """
    run_folder = Path(run_folder)
    run_folder.mkdir(parents=True, exist_ok=True)

    copied_outputs = {}

    for output_name, output_path in outputs.items():
        destination_name = OUTPUT_FILENAMES.get(output_name)

        if output_name == "images" and isinstance(output_path, list):
            images_folder = run_folder / "images"
            images_folder.mkdir(parents=True, exist_ok=True)
            copied_images = []

            for image_path in output_path:
                source_path = Path(image_path)

                if not source_path.exists():
                    continue

                destination_path = images_folder / source_path.name
                shutil.copy2(source_path, destination_path)
                copied_images.append(str(destination_path))

            if copied_images:
                copied_outputs[output_name] = copied_images

            continue

        if not destination_name:
            continue

        source_path = Path(output_path)

        if not source_path.exists():
            continue

        destination_path = run_folder / destination_name
        shutil.copy2(source_path, destination_path)
        copied_outputs[output_name] = str(destination_path)

    return copied_outputs
