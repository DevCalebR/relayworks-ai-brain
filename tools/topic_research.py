import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


TOPIC_OUTPUT_DIR = Path("outputs/topics")
VALID_TEMPLATES = {"default", "bold", "minimal", "ai"}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _safe_filename(value):
    filename = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return filename or "topic-research"


def _score(value, default=1):
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    return max(1, min(10, score))


def _text(value):
    return str(value or "").strip()


def _normalize_topic(raw_topic, rank):
    if not isinstance(raw_topic, dict):
        raw_topic = {}

    viral_score = _score(raw_topic.get("viral_potential_score"))
    difficulty_score = _score(raw_topic.get("production_difficulty_score"))
    suggested_template = _text(raw_topic.get("suggested_template")).lower()

    if suggested_template not in VALID_TEMPLATES:
        suggested_template = "default"

    tags = raw_topic.get("tags", [])
    if not isinstance(tags, list):
        tags = []

    return {
        "rank": rank,
        "topic": _text(raw_topic.get("topic")),
        "hook": _text(raw_topic.get("hook")),
        "why_it_could_work": _text(raw_topic.get("why_it_could_work")),
        "target_audience": _text(raw_topic.get("target_audience")),
        "viral_potential_score": viral_score,
        "production_difficulty_score": difficulty_score,
        "combined_score": round(viral_score - (difficulty_score * 0.3), 2),
        "suggested_template": suggested_template,
        "suggested_image_angle": _text(raw_topic.get("suggested_image_angle")),
        "suggested_thumbnail_angle": _text(raw_topic.get("suggested_thumbnail_angle")),
        "suggested_title": _text(raw_topic.get("suggested_title")),
        "tags": [_text(tag) for tag in tags if _text(tag)],
    }


def _parse_topics(content):
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("OpenAI topic research response was not valid JSON") from exc

    topics = data.get("topics") if isinstance(data, dict) else data
    if not isinstance(topics, list):
        raise ValueError("OpenAI topic research response was not valid JSON")

    normalized_topics = [_normalize_topic(topic, 0) for topic in topics]
    normalized_topics.sort(key=lambda topic: topic["combined_score"], reverse=True)

    for index, topic in enumerate(normalized_topics, start=1):
        topic["rank"] = index

    return normalized_topics


def research_topics(niche, audience=None, count=10):
    if count <= 0:
        raise ValueError("--topic-count must be greater than 0")

    client = _get_client()
    audience_text = audience or "the most likely buyer-facing audience for this niche"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You research weird history, mystery, dark history, unsolved "
                    "disappearance, and scary factual YouTube Shorts ideas using only "
                    "your general knowledge. Ideas must be specific, curiosity-driven, "
                    "and factual-sounding rather than generic categories. "
                    "Do not claim to use YouTube APIs, analytics, trend data, web search, "
                    "or scraped data. Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate {count} promising weird-history or mystery YouTube Shorts topic ideas.\n"
                    f"Niche: {niche}\n"
                    f"Audience: {audience_text}\n\n"
                    "Make each topic specific and curiosity-driven, like:\n"
                    "- The village that vanished overnight\n"
                    "- The king who died from laughing too hard\n"
                    "- The unsolved disappearance inside a locked room\n"
                    "- The ancient punishment people were terrified of\n"
                    "- The island nobody was allowed to visit\n\n"
                    "Avoid generic ideas like Interesting history facts, Scary mysteries, "
                    "or Dark history stories.\n\n"
                    "Return a JSON object with a topics array. Each topic must include:\n"
                    "- topic\n"
                    "- hook\n"
                    "- why_it_could_work\n"
                    "- target_audience\n"
                    "- viral_potential_score, integer 1-10 where higher is better\n"
                    "- production_difficulty_score, integer 1-10 where lower is easier\n"
                    "- suggested_template, one of default, bold, minimal, ai\n"
                    "- suggested_image_angle\n"
                    "- suggested_thumbnail_angle\n"
                    "- suggested_title\n"
                    "- tags, array of short strings\n\n"
                    "Prefer suggested_template bold or ai for eerie, mystery, or dark history "
                    "topics when appropriate."
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI topic research response was not valid JSON")

    return _parse_topics(content)


def save_topic_research(niche, topics, output_name=None):
    TOPIC_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename_base = _safe_filename(output_name or niche)
    output_path = TOPIC_OUTPUT_DIR / f"{filename_base}.json"
    payload = {
        "niche": niche,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_from": "relayworks-ai-brain",
        "topics": topics,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")

    return str(output_path)
