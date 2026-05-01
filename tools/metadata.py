import json
import re
from pathlib import Path


METADATA_OUTPUT_DIR = Path("outputs/metadata")
GENERATED_FROM = "relayworks-ai-brain"
DEFAULT_HASHTAGS = [
    "#shorts",
    "#history",
    "#mystery",
    "#weirdhistory",
    "#darkhistory",
    "#unsolved",
]
DEFAULT_TAGS = [
    "weird history",
    "mystery",
    "dark history",
    "unsolved mystery",
    "eerie true stories",
    "shorts",
    "youtube shorts",
]


def _safe_filename(name):
    safe_name = str(name).lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "metadata"


def _topic_keywords(topic):
    words = re.findall(r"[a-z0-9]+", str(topic).lower())
    ignored_words = {
        "a",
        "an",
        "and",
        "are",
        "for",
        "how",
        "in",
        "is",
        "of",
        "the",
        "to",
        "with",
    }

    keywords = []
    for word in words:
        if len(word) < 3 or word in ignored_words or word in keywords:
            continue
        keywords.append(word)

    return keywords[:8]


def _build_tags(topic, script):
    tags = list(DEFAULT_TAGS)

    for keyword in _topic_keywords(topic):
        if keyword not in tags:
            tags.append(keyword)

    return tags


def save_video_metadata(topic, script, output_name):
    """
    Save local YouTube-ready metadata for a generated video.

    Args:
        topic: Original pipeline topic.
        script: Script text used to create the video.
        output_name: Human-readable name used to create the output filename.

    Returns:
        The saved metadata JSON file path as a string.
    """
    METADATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    clean_topic = str(topic).strip() or "Untitled video"
    output_path = METADATA_OUTPUT_DIR / f"{_safe_filename(output_name)}.json"

    metadata = {
        "title": clean_topic,
        "description": (
            f"A quick weird-history and mystery short about {clean_topic}. "
            "Generated locally with RelayWorks AI Content Brain."
        ),
        "tags": _build_tags(clean_topic, script),
        "hashtags": DEFAULT_HASHTAGS,
        "topic": topic,
        "generated_from": GENERATED_FROM,
    }

    output_path.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    return str(output_path)
