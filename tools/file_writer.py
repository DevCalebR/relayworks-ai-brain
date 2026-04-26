from pathlib import Path
import re


OUTPUTS_DIR = Path("outputs/scripts")


def _safe_filename(topic: str) -> str:
    slug = topic.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "script"


def save_script(topic: str, script: str) -> str:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = OUTPUTS_DIR / f"{_safe_filename(topic)}.txt"
    content = f"Topic: {topic}\n\n{script}"
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)
