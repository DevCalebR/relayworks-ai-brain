import json
import re
from pathlib import Path


METADATA_OUTPUT_DIR = Path("outputs/metadata")
GENERATED_FROM = "relayworks-ai-brain"
DEFAULT_HASHTAGS = [
    "#history",
    "#mystery",
    "#weirdhistory",
    "#darkhistory",
    "#unsolved",
    "#strangehistory",
]
SHORTS_HASHTAGS = ["#shorts", "#historyshorts", "#weirdhistory"]
DEFAULT_TAGS = [
    "weird history",
    "mystery",
    "unsolved mystery",
    "dark history",
    "historical mystery",
    "scary history",
    "true mystery",
    "eerie history",
    "strange history",
    "history documentary",
    "mystery documentary",
    "creepy history",
    "unexplained history",
]
SHORTS_TAGS = [
    "youtube shorts",
    "history shorts",
    "weird history shorts",
    "mystery shorts",
    "true story shorts",
]
ROANOKE_TAGS = [
    "lost colony",
    "lost colony of roanoke",
    "roanoke mystery",
    "roanoke colony",
    "croatoan",
    "american history",
    "colonial history",
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


def _is_ai_or_money_topic(topic):
    topic_text = str(topic).lower()
    return bool(
        re.search(
            r"\b(ai|artificial intelligence|make money|side hustle|sidehustle|income)\b",
            topic_text,
        )
    )


def _dedupe(items):
    deduped = []

    for item in items:
        normalized = str(item).strip()

        if not normalized:
            continue

        if normalized.lower() in [existing.lower() for existing in deduped]:
            continue

        deduped.append(normalized)

    return deduped


def _build_tags(topic, script, content_style="episode"):
    topic_text = str(topic).lower()
    tags = list(DEFAULT_TAGS)

    if content_style == "short":
        tags = SHORTS_TAGS + tags

    if "roanoke" in topic_text or "croatoan" in topic_text:
        tags.extend(ROANOKE_TAGS)

    if "episode" in topic_text:
        tags.extend(["history episode", "mystery episode", "true story episode"])

    for keyword in _topic_keywords(topic):
        tags.append(keyword)

    if script:
        for keyword in _topic_keywords(script):
            tags.append(keyword)

    if _is_ai_or_money_topic(topic):
        tags.extend(["ai", "make money", "side hustle"])

    return _dedupe(tags)[:25]


def _build_hashtags(topic, content_style="episode"):
    hashtags = list(DEFAULT_HASHTAGS)

    if content_style == "short":
        hashtags = SHORTS_HASHTAGS + hashtags

    topic_text = str(topic).lower()
    if "roanoke" in topic_text:
        hashtags.append("#roanoke")
    if "croatoan" in topic_text:
        hashtags.append("#croatoan")

    if _is_ai_or_money_topic(topic):
        hashtags.extend(["#ai", "#makemoney", "#sidehustle"])

    return _dedupe(hashtags)[:8]


def _topic_summary(topic):
    clean_topic = str(topic).strip()
    summary_topic = re.sub(r"\s+episode\s+\d+.*$", "", clean_topic, flags=re.I)
    summary_topic = summary_topic.strip(" :-") or clean_topic

    topic_text = clean_topic.lower()

    if "roanoke" in topic_text:
        return (
            "The Lost Colony of Roanoke is one of the most haunting mysteries in "
            "early American history."
        )

    return (
        f"{summary_topic} is explored as a strange, factual story from history "
        "and mystery."
    )


def _episode_line(topic):
    if "episode" not in str(topic).lower():
        return ""

    return (
        "This episode-style series explores weird history, unsolved mysteries, "
        "dark historical events, and eerie true stories."
    )


def _build_description(topic, hashtags, content_style="episode"):
    clean_topic = str(topic).strip() or "Untitled video"
    topic_text = clean_topic.lower()

    if content_style == "short":
        intro = (
            f"A fast factual Short about {clean_topic}, told for fans of weird "
            "history, mysteries, dark history, and eerie true stories."
        )
        paragraphs = [intro]
        paragraphs.append(
            "If you want more strange stories like this, like this video and subscribe."
        )
        paragraphs.append(" ".join(hashtags))
        return "\n\n".join(paragraphs)

    if "roanoke" in topic_text:
        intro = (
            f"{_topic_summary(clean_topic)} In this episode, we look at the "
            "settlement that vanished, the people left behind, and the strange "
            "silence that greeted the rescuers when they returned."
        )
    else:
        intro = (
            f"{_topic_summary(clean_topic)} In this episode-style weird history "
            "and mystery story, we follow the key details, unanswered questions, "
            "and eerie facts behind the case."
        )

    paragraphs = [intro]
    series_line = _episode_line(clean_topic)

    if series_line:
        paragraphs.append(series_line)

    paragraphs.append(
        "If you want more strange stories like this, like this video and subscribe."
    )
    paragraphs.append(" ".join(hashtags))

    return "\n\n".join(paragraphs)


def save_video_metadata(topic, script, output_name, content_style="episode"):
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
    hashtags = _build_hashtags(clean_topic, content_style=content_style)

    metadata = {
        "title": clean_topic,
        "description": _build_description(
            clean_topic,
            hashtags,
            content_style=content_style,
        ),
        "tags": _build_tags(clean_topic, script, content_style=content_style),
        "hashtags": hashtags,
        "topic": topic,
        "content_style": content_style,
        "generated_from": GENERATED_FROM,
    }

    output_path.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    return str(output_path)
