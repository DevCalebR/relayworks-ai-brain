from pathlib import Path


SUPPORTED_SCRIPT_EXTENSIONS = {".txt", ".md"}


def read_script_file(script_path):
    """
    Read a user-provided narration script from a local text file.

    Args:
        script_path: Local .txt or .md script path.

    Returns:
        The stripped script text as a string.
    """
    path = Path(script_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Script file does not exist: {script_path}")

    if not path.is_file():
        raise ValueError(f"Script path must be a file: {script_path}")

    if path.suffix.lower() not in SUPPORTED_SCRIPT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_SCRIPT_EXTENSIONS))
        raise ValueError(
            f"Unsupported script file extension: {path.suffix or '(none)'}. "
            f"Supported extensions: {supported}"
        )

    try:
        script = path.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValueError(f"Script file must be UTF-8 encoded: {script_path}") from exc

    if not script:
        raise ValueError(f"Script file is empty: {script_path}")

    return script
