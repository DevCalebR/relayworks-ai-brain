import json
import re
from pathlib import Path


METADATA_OUTPUT_DIR = Path("outputs/metadata")
GENERATED_FROM = "relayworks-ai-brain"
CTA_LINE = "If you want more strange stories like this, like this video and subscribe."
SERIES_POSITIONING = (
    "This series explores weird history, unsolved mysteries, dark historical "
    "events, and eerie true stories."
)
SERIES_EPISODE_POSITIONING = (
    "This episode is part of a series exploring weird history, unsolved "
    "mysteries, dark historical events, and eerie true stories."
)
DEFAULT_HASHTAGS = [
    "#WeirdHistory",
    "#Mystery",
    "#DarkHistory",
    "#UnsolvedMystery",
    "#StrangeHistory",
]
SHORTS_HASHTAGS = ["#shorts", "#historyshorts", "#weirdhistory"]
DEFAULT_TAGS = [
    "history",
    "mystery",
    "weird history",
    "dark history",
    "unsolved mystery",
    "historical mystery",
    "eerie true stories",
    "strange history",
    "strange true stories",
    "scary history",
    "true mystery",
    "eerie history",
    "history mystery",
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
TOPIC_PROFILES = [
    {
        "keywords": ("roanoke", "lost colony", "croatoan"),
        "tags": [
            "Roanoke",
            "Lost Colony",
            "Lost Colony of Roanoke",
            "Croatoan",
            "Roanoke mystery",
            "American history",
            "colonial history",
        ],
        "hashtags": ["#Roanoke", "#LostColony", "#Croatoan"],
        "hook": (
            "The Lost Colony of Roanoke left behind an empty settlement, a few "
            "carved letters, and a historical record that refuses to close. "
            "This episode follows the evidence without turning uncertainty into "
            "legend."
        ),
        "summary": (
            "This episode covers the colony's disappearance, the delayed return "
            "to Roanoke Island, the Croatoan clue, and the cautious explanations "
            "historians still weigh today."
        ),
    },
    {
        "keywords": ("flannan", "eilean mor", "lighthouse keepers"),
        "tags": [
            "Flannan Isles",
            "Flannan Isles lighthouse",
            "lighthouse mystery",
            "missing lighthouse keepers",
            "Scottish history",
            "maritime mystery",
        ],
        "hashtags": ["#FlannanIsles", "#LighthouseMystery", "#UnsolvedMystery"],
        "hook": (
            "When the relief vessel reached the Flannan Isles lighthouse in "
            "December 1900, three keepers were gone and the station was silent. "
            "The mystery endures because the surviving record leaves unsettling "
            "gaps."
        ),
        "summary": (
            "This episode covers the missing keepers, the condition of the "
            "lighthouse, the weather and logbook questions, and the grounded "
            "theories that still compete with later retellings."
        ),
    },
    {
        "keywords": ("mary celeste",),
        "tags": [
            "Mary Celeste",
            "Mary Celeste mystery",
            "ghost ship",
            "abandoned ship",
            "maritime mystery",
            "Atlantic history",
        ],
        "hashtags": ["#MaryCeleste", "#MaritimeMystery", "#UnsolvedMystery"],
        "hook": (
            "The Mary Celeste was found adrift in 1872 with its crew missing and "
            "much of the ship still intact. The evidence points to danger, but "
            "it never fully explains why everyone left."
        ),
        "summary": (
            "This episode covers the ship's final voyage, what rescuers found "
            "aboard, which details are often exaggerated, and why the case "
            "remains one of history's most famous maritime mysteries."
        ),
    },
    {
        "keywords": ("dancing plague", "dancing mania", "strasbourg 1518"),
        "tags": [
            "Dancing Plague",
            "Dancing Plague of 1518",
            "Strasbourg 1518",
            "dancing mania",
            "medical history",
            "strange historical events",
        ],
        "hashtags": ["#DancingPlague", "#StrangeHistory", "#WeirdHistory"],
        "hook": (
            "In 1518, people in Strasbourg were reported to dance for days in "
            "one of Europe's strangest recorded outbreaks. The story is eerie "
            "because the records describe real suffering without offering one "
            "simple answer."
        ),
        "summary": (
            "This episode covers what the historical accounts say, how the "
            "outbreak spread through the city, the explanations historians "
            "consider, and which dramatic claims should be treated carefully."
        ),
    },
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
        "part",
        "episode",
        "the",
        "this",
        "to",
        "video",
        "with",
    }

    keywords = []
    for word in words:
        if len(word) < 3 or word in ignored_words or word in keywords:
            continue
        keywords.append(word)

    return keywords[:8]


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


def _clean_topic(topic):
    return re.sub(r"\s+", " ", str(topic).strip()) or "Untitled video"


def _split_episode_topic(topic):
    clean_topic = _clean_topic(topic)
    match = re.search(
        r"\s+(episode\s+\d+[a-z]?)\s*[:\-]\s*(.+)$",
        clean_topic,
        flags=re.I,
    )

    if not match:
        return clean_topic, "", ""

    base_topic = clean_topic[: match.start()].strip(" :-")
    episode_label = match.group(1).strip()
    episode_title = match.group(2).strip(" :-")

    return base_topic or clean_topic, episode_label, episode_title


def _topic_profile(topic):
    topic_text = str(topic).lower()

    for profile in TOPIC_PROFILES:
        if any(keyword in topic_text for keyword in profile["keywords"]):
            return profile

    return None


def _is_episode_topic(topic):
    return bool(re.search(r"\bepisode\b", str(topic), flags=re.I))


def _generic_hook(topic):
    base_topic, _, _ = _split_episode_topic(topic)

    return (
        f"{base_topic} begins with a question the historical record cannot fully "
        "close. This episode follows the known details, the uneasy gaps, and the "
        "facts that keep the mystery alive."
    )


def _generic_summary(topic):
    base_topic, _, episode_title = _split_episode_topic(topic)
    focus = base_topic

    if episode_title:
        focus = f"{base_topic}, including {episode_title}"

    return (
        f"This episode covers the setting, timeline, key evidence, and unanswered "
        f"questions behind {focus}, separating grounded details from later legend "
        "where the record is uncertain."
    )


def build_topic_tags(topic, script=None, content_style="episode"):
    """Build deterministic YouTube tags for weird history and mystery videos."""
    topic_text = str(topic).lower()
    tags = list(DEFAULT_TAGS)

    if content_style == "short":
        tags = SHORTS_TAGS + tags

    profile = _topic_profile(topic)
    if profile:
        tags.extend(profile["tags"])

    if "episode" in topic_text:
        tags.extend(
            [
                "history episode",
                "mystery episode",
                "weird history episode",
                "true story episode",
                "episode series",
            ]
        )

    for keyword in _topic_keywords(topic):
        tags.append(keyword)

    if script:
        for keyword in _topic_keywords(script):
            tags.append(keyword)

    return _dedupe(tags)[:25]


def build_topic_hashtags(topic, content_style="episode"):
    """Build a compact, non-spammy hashtag set for the metadata description."""
    profile = _topic_profile(topic)
    hashtags = list(profile["hashtags"]) if profile else []

    if content_style == "short":
        hashtags = SHORTS_HASHTAGS + hashtags

    hashtags.extend(DEFAULT_HASHTAGS)

    return _dedupe(hashtags)[:6]


def _build_short_description(topic, hashtags):
    clean_topic = _clean_topic(topic)
    profile = _topic_profile(clean_topic)
    summary = profile["summary"] if profile else _generic_summary(clean_topic)

    paragraphs = [
        (
            f"A focused factual Short about {clean_topic}, told for viewers who "
            "follow weird history, mysteries, dark history, and eerie true stories."
        ),
        summary,
        CTA_LINE,
        " ".join(hashtags),
    ]

    return "\n\n".join(paragraphs)


def build_video_description(topic, script=None, content_style="episode", hashtags=None):
    """Build a polished local YouTube description without calling external APIs."""
    clean_topic = _clean_topic(topic)
    selected_hashtags = hashtags or build_topic_hashtags(
        clean_topic,
        content_style=content_style,
    )

    if content_style == "short":
        return _build_short_description(clean_topic, selected_hashtags)

    profile = _topic_profile(clean_topic)
    hook = profile["hook"] if profile else _generic_hook(clean_topic)
    summary = profile["summary"] if profile else _generic_summary(clean_topic)
    series_line = (
        SERIES_EPISODE_POSITIONING
        if _is_episode_topic(clean_topic)
        else SERIES_POSITIONING
    )

    paragraphs = [
        hook,
        summary,
        series_line,
        CTA_LINE,
        " ".join(selected_hashtags),
    ]

    return "\n\n".join(paragraphs)


def _build_tags(topic, script, content_style="episode"):
    return build_topic_tags(topic, script=script, content_style=content_style)


def _build_hashtags(topic, content_style="episode"):
    return build_topic_hashtags(topic, content_style=content_style)


def _build_description(topic, hashtags, content_style="episode"):
    return build_video_description(
        topic,
        content_style=content_style,
        hashtags=hashtags,
    )


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

    clean_topic = _clean_topic(topic)
    output_path = METADATA_OUTPUT_DIR / f"{_safe_filename(output_name)}.json"
    hashtags = build_topic_hashtags(clean_topic, content_style=content_style)

    metadata = {
        "title": clean_topic,
        "description": build_video_description(
            clean_topic,
            script=script,
            content_style=content_style,
            hashtags=hashtags,
        ),
        "tags": build_topic_tags(
            clean_topic,
            script=script,
            content_style=content_style,
        ),
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
