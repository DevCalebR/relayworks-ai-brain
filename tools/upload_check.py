import json
from pathlib import Path

from moviepy import VideoFileClip


REQUIRED_FILES = ("video.mp4", "metadata.json")
RECOMMENDED_FILES = ("captions.srt", "script.txt", "audio.mp3")
REQUIRED_METADATA_FIELDS = (
    "title",
    "description",
    "tags",
    "hashtags",
    "topic",
    "generated_from",
)


def _file_status(run_path, filename):
    file_path = run_path / filename

    return {
        "path": str(file_path),
        "exists": file_path.exists(),
        "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
    }


def _validate_video(video_path, errors):
    if not video_path.exists():
        return None

    if video_path.stat().st_size <= 0:
        errors.append("Required file is empty: video.mp4")
        return None

    try:
        video_clip = VideoFileClip(str(video_path))
    except Exception as exc:
        errors.append(f"video.mp4 could not be read: {exc}")
        return None

    try:
        duration = video_clip.duration
    finally:
        video_clip.close()

    if duration <= 0:
        errors.append("video.mp4 duration must be greater than 0 seconds")

    return duration


def _validate_metadata(metadata_path, errors):
    metadata_result = {
        "path": str(metadata_path),
        "valid_json": False,
        "required_fields": {},
    }

    if not metadata_path.exists():
        return metadata_result

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"metadata.json is not valid JSON: {exc}")
        return metadata_result

    metadata_result["valid_json"] = True

    if not isinstance(metadata, dict):
        errors.append("metadata.json must contain a JSON object")
        return metadata_result

    for field in REQUIRED_METADATA_FIELDS:
        metadata_result["required_fields"][field] = field in metadata

        if field not in metadata:
            errors.append(f"metadata.json is missing required field: {field}")

    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        errors.append("metadata.json title must be a non-empty string")

    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("metadata.json description must be a non-empty string")

    if not isinstance(metadata.get("tags"), list):
        errors.append("metadata.json tags must be a list")

    if not isinstance(metadata.get("hashtags"), list):
        errors.append("metadata.json hashtags must be a list")

    return metadata_result


def validate_upload_package(run_folder):
    """
    Validate an organized local run folder for future YouTube upload readiness.

    This function only checks local files and metadata. It does not upload
    anything, call YouTube, or require YouTube credentials.
    """
    run_path = Path(run_folder)

    if not run_path.exists():
        raise FileNotFoundError(f"Run folder does not exist: {run_folder}")

    errors = []
    warnings = []

    required_files = {
        filename: _file_status(run_path, filename) for filename in REQUIRED_FILES
    }
    recommended_files = {
        filename: _file_status(run_path, filename) for filename in RECOMMENDED_FILES
    }

    for filename, status in required_files.items():
        if not status["exists"]:
            errors.append(f"Required file is missing: {filename}")

    for filename, status in recommended_files.items():
        if not status["exists"]:
            warnings.append(f"Recommended file is missing: {filename}")

    metadata_result = _validate_metadata(run_path / "metadata.json", errors)
    video_duration = _validate_video(run_path / "video.mp4", errors)

    if video_duration is not None:
        required_files["video.mp4"]["duration_seconds"] = video_duration

    return {
        "ready": not errors,
        "run_folder": str(run_path),
        "required_files": required_files,
        "recommended_files": recommended_files,
        "metadata": metadata_result,
        "warnings": warnings,
        "errors": errors,
    }
