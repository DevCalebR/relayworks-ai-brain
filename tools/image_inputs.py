from pathlib import Path


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _is_supported_image(path):
    return path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def collect_image_paths(images_dir=None, image_paths=None):
    """
    Collect supported local image paths from an optional directory and path list.

    Args:
        images_dir: Optional directory containing local image files.
        image_paths: Optional iterable of explicit local image paths.

    Returns:
        A deduplicated list of supported image file paths as strings.
    """
    collected_paths = []

    if images_dir:
        directory = Path(images_dir).expanduser()

        if not directory.exists():
            raise FileNotFoundError(f"Images directory does not exist: {images_dir}")

        if not directory.is_dir():
            raise ValueError(f"--images-dir must be a directory: {images_dir}")

        directory_images = sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and _is_supported_image(path)
        )

        if not directory_images:
            extensions = ", ".join(sorted(SUPPORTED_IMAGE_EXTENSIONS))
            raise ValueError(
                f"Images directory contains no supported images ({extensions}): "
                f"{images_dir}"
            )

        collected_paths.extend(directory_images)

    for image_path in image_paths or []:
        path = Path(image_path).expanduser()

        if not path.exists():
            raise FileNotFoundError(f"Image path does not exist: {image_path}")

        if not path.is_file():
            raise ValueError(f"--image-paths entries must be files: {image_path}")

        if _is_supported_image(path):
            collected_paths.append(path)

    deduplicated_paths = []
    seen_paths = set()

    for path in collected_paths:
        resolved_path = path.resolve()

        if resolved_path in seen_paths:
            continue

        seen_paths.add(resolved_path)
        deduplicated_paths.append(str(resolved_path))

    return deduplicated_paths
