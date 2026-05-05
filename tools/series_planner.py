import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

SERIES_OUTPUT_DIR = Path("outputs/series")
VALID_TEMPLATES = {"default", "bold", "minimal", "ai"}
VALID_VIDEO_FORMATS = {"landscape", "vertical"}
DEFAULT_SUGGESTED_TEMPLATE = "ai"
DEFAULT_SUGGESTED_IMAGE_COUNT = 12
DEFAULT_SUGGESTED_VIDEO_FORMAT = "landscape"
DEFAULT_AUDIENCE = "fans of weird history, mysteries, and eerie factual stories"
DEFAULT_TARGET_DURATION_SECONDS = 150
DEFAULT_SERIES_TONE = "eerie, factual, cinematic, and suspenseful"
DEFAULT_FACTUAL_GUARDRAILS = [
    "Use careful factual-edutainment framing and verify historical details during human review.",
    "Frame uncertain or disputed details as uncertain, disputed, folklore, or later retellings.",
    "Do not present unsupported claims, invented evidence, or speculation as established fact.",
]
DEFAULT_WHAT_IS_KNOWN = (
    "Known details should be verified during human review. The plan should rely only on "
    "topic-relevant historical information."
)
DEFAULT_WHAT_IS_UNCERTAIN = (
    "Uncertain details should be framed as uncertain, disputed, or omitted."
)
DEFAULT_WHAT_NOT_TO_CLAIM = (
    "Do not present unsupported claims, folklore, theories, invented evidence, or disputed "
    "details as established fact."
)
DEFAULT_SOURCE_SENSITIVITY_NOTES = [
    "Historical retellings may exaggerate details; review dates, names, locations, evidence descriptions, and theories before production.",
]
DEFAULT_SERIES_NARRATIVE_ARC = (
    "The series should begin with the central mystery, escalate through context and "
    "evidence, test the strongest explanations, and end with a careful account of "
    "what the record can and cannot resolve."
)
GENERIC_EVIDENCE_TERMS = {
    "letters",
    "documents",
    "expert commentary",
    "expert opinions",
    "historical sources",
    "interviews",
    "medical records",
    "modern theories",
    "official sentiment",
    "personal accounts",
    "historical documents",
    "psychological studies",
    "recorded statements",
    "scholarly articles",
    "testimonies",
    "unnamed sources",
}
GENERIC_TITLE_PHRASES = {
    "the beginning",
    "the evidence",
    "the theories",
    "the legacy",
    "life before the mystery",
    "what happened",
}
SENSATIONAL_TITLE_PHRASES = {
    "dancing until dead",
    "the killer dance",
    "everyone died dancing",
    "the curse that killed them",
}
SUSPICIOUS_TOPIC_TERMS = {
    "cryptic notes",
    "empty ship",
    "drifting vessel",
    "adrift ship",
    "driftwood boat",
    "lifeboat",
}
SHIP_MISMATCH_TERMS = {
    "empty ship",
    "ghost ship",
    "drifting vessel",
    "adrift ship",
    "driftwood boat",
    "lifeboat",
}
SHIP_TITLE_WORDS = {
    "ship",
    "ships",
    "vessel",
    "vessels",
    "boat",
    "boats",
    "lifeboat",
    "lifeboats",
    "schooner",
    "brigantine",
}
LIGHTHOUSE_TITLE_WORDS = {
    "lighthouse",
    "lighthouses",
    "keeper",
    "keepers",
    "logbook",
    "logbooks",
}
DISPUTED_QUALIFIERS = {
    "disputed",
    "folklore",
    "legend",
    "later retelling",
    "later retellings",
    "unverified",
    "unsupported",
    "claimed",
    "alleged",
}
OVERSTATEMENT_REPLACEMENTS = {
    "perfectly untouched": "with no obvious signs of violence",
    "no one can explain": "the official record does not fully explain",
    "experts agree": "some interpretations suggest",
}


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _safe_slug(value):
    slug = str(value).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "series"


def _episode_filename(episode_number):
    return f"episode-{int(episode_number):02d}.md"


def _extract_json(content):
    if not content or not content.strip():
        raise ValueError("OpenAI returned an empty series plan response")

    text = content.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError("OpenAI returned invalid JSON for the series plan")

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"OpenAI returned invalid JSON for the series plan: {exc}"
            ) from exc


def _validate_series_plan(series_plan, expected_episodes=None):
    required_fields = [
        "series_title",
        "topic",
        "audience",
        "target_duration_seconds",
        "episode_count",
        "tone",
        "factual_guardrails",
        "series_narrative_arc",
        "what_is_known",
        "what_is_uncertain",
        "what_not_to_claim",
        "source_sensitivity_notes",
        "key_people_or_groups",
        "timeline",
    ]

    missing = [field for field in required_fields if field not in series_plan]
    if missing:
        raise ValueError(f"Series plan is missing required fields: {', '.join(missing)}")

    episode_plan = series_plan.get("episode_plan")
    if not isinstance(episode_plan, list) or not episode_plan:
        raise ValueError("Series plan episode_plan must be a non-empty list")

    if expected_episodes is not None and len(episode_plan) != expected_episodes:
        raise ValueError(
            f"Series plan expected {expected_episodes} episodes but got {len(episode_plan)}"
        )

    episode_required_fields = [
        "episode_number",
        "title",
        "episode_topic",
        "hook",
        "chapter_summary",
        "key_beats",
        "continuity_from_previous",
        "ending_tease",
        "next_episode_setup",
        "suggested_template",
        "suggested_image_count",
        "suggested_thumbnail_angle",
        "suggested_video_format",
        "evidence_focus",
        "avoid_repeating",
    ]

    episode_numbers = []
    for episode in episode_plan:
        if not isinstance(episode, dict):
            raise ValueError("Each episode_plan item must be an object")

        missing_episode_fields = [
            field for field in episode_required_fields if field not in episode
        ]
        if missing_episode_fields:
            episode_number = episode.get("episode_number", "unknown")
            raise ValueError(
                "Episode plan item "
                f"{episode_number} is missing fields: {', '.join(missing_episode_fields)}"
            )

        if not str(episode.get("title", "")).strip():
            raise ValueError("Episode plan item title must be a non-empty string")

        if not str(episode.get("chapter_summary", "")).strip():
            episode_number = episode.get("episode_number", "unknown")
            raise ValueError(
                f"Episode plan item {episode_number} chapter_summary must be non-empty"
            )

        try:
            episode["episode_number"] = int(episode["episode_number"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Episode plan item episode_number must be an integer") from exc
        episode_numbers.append(episode["episode_number"])

        for list_field in ["key_beats", "evidence_focus", "avoid_repeating"]:
            if not isinstance(episode.get(list_field), list):
                episode_number = episode.get("episode_number", "unknown")
                raise ValueError(
                    f"Episode plan item {episode_number} {list_field} must be a list"
                )

        if episode.get("suggested_template") not in VALID_TEMPLATES:
            raise ValueError(
                "Episode plan item suggested_template must be one of: "
                + ", ".join(sorted(VALID_TEMPLATES))
            )

        if not isinstance(episode.get("suggested_image_count"), int):
            raise ValueError("Episode plan item suggested_image_count must be an integer")

        if episode.get("suggested_video_format") not in VALID_VIDEO_FORMATS:
            raise ValueError(
                "Episode plan item suggested_video_format must be landscape or vertical"
            )

    if expected_episodes is not None:
        expected_numbers = list(range(1, expected_episodes + 1))
        if episode_numbers != expected_numbers:
            raise ValueError(
                "Series plan episode numbers must be sequential from 1 to "
                f"{expected_episodes}"
            )

    _validate_topic_containment(series_plan)


def _normalize_template(value):
    template = str(value or "").strip().lower()
    if template in VALID_TEMPLATES:
        return template
    if "bold" in template or "tension" in template:
        return "bold"
    return DEFAULT_SUGGESTED_TEMPLATE


def _normalize_image_count(value):
    if value is None:
        return DEFAULT_SUGGESTED_IMAGE_COUNT

    try:
        image_count = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SUGGESTED_IMAGE_COUNT

    return image_count if image_count > 0 else DEFAULT_SUGGESTED_IMAGE_COUNT


def _normalize_list(value, default_item=None):
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return [default_item] if default_item else []
    return [str(value)]


def _normalize_video_format(value):
    video_format = str(value or "").strip().lower()
    if video_format in VALID_VIDEO_FORMATS:
        return video_format
    return DEFAULT_SUGGESTED_VIDEO_FORMAT


def _set_default_if_missing(target, key, value):
    if target.get(key) in [None, ""]:
        if isinstance(value, list):
            value = list(value)
        target[key] = value


def _parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _contains_phrase(text, phrase):
    return phrase in str(text or "").lower()


def _contains_any_phrase(text, phrases):
    normalized = str(text or "").lower()
    return any(phrase in normalized for phrase in phrases)


def _contains_any_word(text, words):
    normalized = str(text or "").lower()
    return any(re.search(rf"\b{re.escape(word)}\b", normalized) for word in words)


def _title_needs_story_repair(title):
    normalized = str(title or "").strip().lower()
    if not normalized:
        return True
    return normalized in GENERIC_TITLE_PHRASES or normalized in SENSATIONAL_TITLE_PHRASES


def _default_story_job(episode_number, episode_count):
    if episode_count == 5:
        jobs = {
            1: "Open with the strongest hook and establish why the mystery matters.",
            2: "Build pressure through backstory, timeline, and context without becoming a dry history dump.",
            3: "Separate the strongest evidence and contradictions from later retellings.",
            4: "Test the leading theories, what they explain, and what they fail to explain.",
            5: "Deliver a careful finale with legacy, strongest explanation, and what remains unknown.",
        }
        return jobs.get(episode_number)

    if episode_number == 1:
        return "Open with the strongest hook and establish why the mystery matters."
    if episode_count and episode_number == episode_count:
        return "Deliver a careful finale that resolves what can be resolved and names what remains unknown."
    return "Advance the serialized story with new evidence, context, or tension."


def _default_final_closing_thought(series_plan):
    topic = str(series_plan.get("topic") or "the mystery").strip()
    return (
        f"The records can narrow what people feared about {topic}. They still cannot "
        "fully tell us what happened inside the moment when the mystery began."
    )


def _topic_profile(series_plan):
    topic_text = " ".join(
        str(series_plan.get(field, ""))
        for field in ["topic", "series_title"]
    ).lower()
    return {
        "is_lighthouse_topic": _contains_any_word(
            topic_text,
            {
                "lighthouse",
                "lighthouses",
                "flannan",
                "keeper",
                "keepers",
            },
        ),
        "is_ship_topic": _contains_any_word(
            topic_text,
            {
                "ship",
                "ships",
                "vessel",
                "vessels",
                "boat",
                "boats",
                "schooner",
                "brigantine",
                "mary",
                "celeste",
            },
        ),
    }


def _has_disputed_qualifier(text):
    return _contains_any_phrase(text, DISPUTED_QUALIFIERS)


def _is_term_supported_or_disputed(series_plan, episode, term):
    if _has_disputed_qualifier(episode.get("source_sensitivity_notes", "")):
        return True

    support_fields = [
        series_plan.get("what_is_known", []),
        series_plan.get("what_is_uncertain", []),
        series_plan.get("source_sensitivity_notes", []),
        episode.get("chapter_summary", ""),
        episode.get("key_beats", []),
    ]
    for field in support_fields:
        if isinstance(field, list):
            values = field
        else:
            values = [field]
        for value in values:
            if _contains_phrase(value, term) and _has_disputed_qualifier(value):
                return True

    return False


def _detail_is_mismatched_for_topic(text, profile):
    if profile["is_lighthouse_topic"] and not profile["is_ship_topic"]:
        return _contains_any_phrase(text, SHIP_MISMATCH_TERMS)
    if profile["is_ship_topic"] and not profile["is_lighthouse_topic"]:
        return _contains_any_word(text, LIGHTHOUSE_TITLE_WORDS)
    return False


def _title_is_mismatched_for_topic(title, profile):
    if profile["is_lighthouse_topic"] and not profile["is_ship_topic"]:
        return _contains_any_word(title, SHIP_TITLE_WORDS)
    if profile["is_ship_topic"] and not profile["is_lighthouse_topic"]:
        return _contains_any_word(title, LIGHTHOUSE_TITLE_WORDS)
    return False


def _sanitize_unsupported_claims(text, series_plan, episode, profile):
    if not isinstance(text, str) or not text:
        return text

    sanitized = text
    for overstatement, replacement in OVERSTATEMENT_REPLACEMENTS.items():
        sanitized = re.sub(
            re.escape(overstatement),
            replacement,
            sanitized,
            flags=re.I,
        )

    for term in SUSPICIOUS_TOPIC_TERMS:
        if not _contains_phrase(sanitized, term):
            continue
        if _detail_is_mismatched_for_topic(sanitized, profile):
            sanitized = re.sub(
                re.escape(term),
                "an unsupported detail from another case",
                sanitized,
                flags=re.I,
            )
            continue
        if not _is_term_supported_or_disputed(series_plan, episode, term):
            sanitized = re.sub(
                re.escape(term),
                "a disputed or unsupported detail",
                sanitized,
                flags=re.I,
            )

    return sanitized


def _normalize_evidence_focus(series_plan, episode, profile):
    normalized_evidence = []
    for item in episode.get("evidence_focus", []):
        evidence_item = str(item).strip()
        if not evidence_item:
            continue

        evidence_lower = evidence_item.lower()
        if any(term in evidence_lower for term in GENERIC_EVIDENCE_TERMS):
            continue

        if _detail_is_mismatched_for_topic(evidence_item, profile):
            continue

        should_drop = False
        for term in SUSPICIOUS_TOPIC_TERMS:
            if term not in evidence_lower:
                continue
            if _is_term_supported_or_disputed(series_plan, episode, term):
                if not _has_disputed_qualifier(evidence_item):
                    evidence_item = f"Disputed folklore: {evidence_item}"
                continue
            should_drop = True
            break

        if not should_drop:
            normalized_evidence.append(evidence_item)

    if normalized_evidence:
        return normalized_evidence

    return [
        "No concrete topic-relevant evidence specified; treat this episode as interpretive and avoid overclaiming.",
    ]


def _normalize_episode_topic_containment(series_plan):
    profile = _topic_profile(series_plan)
    for episode in series_plan.get("episode_plan", []):
        if not isinstance(episode, dict):
            continue

        if _title_is_mismatched_for_topic(episode.get("title", ""), profile):
            fallback_title = episode.get("episode_topic", "")
            if not _title_is_mismatched_for_topic(fallback_title, profile):
                episode["title"] = fallback_title
            else:
                episode_number = episode.get("episode_number", "")
                episode["title"] = f"Episode {episode_number}: Evidence and Timeline".strip()

        episode["evidence_focus"] = _normalize_evidence_focus(
            series_plan,
            episode,
            profile,
        )
        episode["chapter_summary"] = _sanitize_unsupported_claims(
            episode.get("chapter_summary", ""),
            series_plan,
            episode,
            profile,
        )
        episode["ending_tease"] = _sanitize_unsupported_claims(
            episode.get("ending_tease", ""),
            series_plan,
            episode,
            profile,
        )

    return series_plan


def _normalize_series_plan(
    series_plan,
    topic=None,
    episodes=None,
    target_duration_seconds=None,
    audience=None,
):
    if not isinstance(series_plan, dict):
        raise ValueError("Series plan must be a JSON object")

    fallback_topic = topic or "Untitled Series"
    fallback_episode_count = episodes
    if fallback_episode_count is None and isinstance(
        series_plan.get("episode_plan"),
        list,
    ):
        fallback_episode_count = _parse_positive_int(series_plan.get("episode_count"))
        if fallback_episode_count is None:
            fallback_episode_count = len(series_plan["episode_plan"])
    expected_for_numbering = _parse_positive_int(fallback_episode_count)

    _set_default_if_missing(
        series_plan,
        "series_title",
        str(fallback_topic).strip() or "Untitled Series",
    )
    _set_default_if_missing(series_plan, "topic", fallback_topic)
    _set_default_if_missing(series_plan, "audience", audience or DEFAULT_AUDIENCE)
    _set_default_if_missing(
        series_plan,
        "target_duration_seconds",
        target_duration_seconds or DEFAULT_TARGET_DURATION_SECONDS,
    )
    _set_default_if_missing(series_plan, "episode_count", fallback_episode_count)
    _set_default_if_missing(series_plan, "tone", DEFAULT_SERIES_TONE)
    _set_default_if_missing(series_plan, "factual_guardrails", DEFAULT_FACTUAL_GUARDRAILS)
    _set_default_if_missing(
        series_plan,
        "series_narrative_arc",
        DEFAULT_SERIES_NARRATIVE_ARC,
    )
    _set_default_if_missing(series_plan, "what_is_known", DEFAULT_WHAT_IS_KNOWN)
    _set_default_if_missing(series_plan, "what_is_uncertain", DEFAULT_WHAT_IS_UNCERTAIN)
    _set_default_if_missing(series_plan, "what_not_to_claim", DEFAULT_WHAT_NOT_TO_CLAIM)
    _set_default_if_missing(
        series_plan,
        "source_sensitivity_notes",
        DEFAULT_SOURCE_SENSITIVITY_NOTES,
    )
    _set_default_if_missing(series_plan, "key_people_or_groups", [])
    _set_default_if_missing(series_plan, "timeline", [])

    series_plan = _normalize_episode_defaults(series_plan)
    series_plan = _normalize_episode_numbers(series_plan, expected_for_numbering)
    return _normalize_episode_topic_containment(series_plan)


def _validate_topic_containment(series_plan):
    profile = _topic_profile(series_plan)
    for episode in series_plan.get("episode_plan", []):
        episode_number = episode.get("episode_number", "unknown")
        if _title_is_mismatched_for_topic(episode.get("title", ""), profile):
            raise ValueError(
                f"Episode plan item {episode_number} title appears unrelated to the requested topic"
            )

        for evidence_item in episode.get("evidence_focus", []):
            if _detail_is_mismatched_for_topic(evidence_item, profile):
                raise ValueError(
                    f"Episode plan item {episode_number} evidence_focus contains topic-mismatched evidence"
                )


def _normalize_episode_defaults(series_plan):
    episode_count = _parse_positive_int(series_plan.get("episode_count"))
    for episode in series_plan.get("episode_plan", []):
        if not isinstance(episode, dict):
            continue

        episode["suggested_template"] = _normalize_template(
            episode.get("suggested_template")
        )
        episode["suggested_image_count"] = _normalize_image_count(
            episode.get("suggested_image_count")
        )
        episode["suggested_video_format"] = _normalize_video_format(
            episode.get("suggested_video_format")
        )

        if not episode.get("episode_topic"):
            episode["episode_topic"] = episode.get("title", "")

        try:
            episode["episode_number"] = int(episode["episode_number"])
        except (KeyError, TypeError, ValueError):
            pass

        episode_number = _parse_positive_int(episode.get("episode_number"))
        episode["story_job"] = str(
            episode.get("story_job")
            or _default_story_job(episode_number, episode_count)
            or "Advance the serialized story with new evidence, context, or tension."
        )

        if _title_needs_story_repair(episode.get("title")):
            episode_topic = str(episode.get("episode_topic", "")).strip()
            if episode_topic and not _title_needs_story_repair(episode_topic):
                episode["title"] = episode_topic
            elif episode_number:
                episode["title"] = f"Episode {episode_number}: Evidence and Tension"
            else:
                episode["title"] = "Evidence and Tension"

        episode["key_beats"] = _normalize_list(episode.get("key_beats"))
        episode["evidence_focus"] = _normalize_list(
            episode.get("evidence_focus"),
            "No concrete evidence specified; treat this episode as interpretive and avoid overclaiming.",
        )
        episode["avoid_repeating"] = _normalize_list(episode.get("avoid_repeating"))

        episode.setdefault("hook", "")
        episode.setdefault("continuity_from_previous", "")
        episode.setdefault("ending_tease", "")
        episode.setdefault("next_episode_setup", "")
        episode.setdefault("suggested_thumbnail_angle", "")

        if episode_count and episode_number == episode_count:
            episode["final_closing_thought"] = str(
                episode.get("final_closing_thought")
                or _default_final_closing_thought(series_plan)
            )

    return series_plan


def _normalize_episode_numbers(series_plan, expected_episodes=None):
    episode_plan = series_plan.get("episode_plan")
    if expected_episodes is None or not isinstance(episode_plan, list):
        return series_plan

    if len(episode_plan) != expected_episodes:
        return series_plan

    for index, episode in enumerate(episode_plan, start=1):
        if isinstance(episode, dict):
            episode["episode_number"] = index

    series_plan["episode_count"] = expected_episodes
    return series_plan


def create_series_plan(
    topic,
    episodes=5,
    target_duration_seconds=150,
    audience=None,
):
    if episodes <= 0:
        raise ValueError("episodes must be greater than 0")
    if target_duration_seconds <= 0:
        raise ValueError("target_duration_seconds must be greater than 0")

    audience_text = audience or DEFAULT_AUDIENCE
    client = _get_client()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You create factual edutainment series plans for weird history, "
                    "mysteries, scary factual stories, dark history, strange historical "
                    "events, and eerie true stories. Create a factual mystery/history "
                    "series bible, a clear chaptered story, and episode plans that are "
                    "specific, dramatic, and useful for batch video generation. The source "
                    "material must be factual-edutainment, not fictional horror. Factual "
                    "accuracy is more important than drama. Do not invent dates, launch "
                    "years, names, people, locations, cargo, evidence, quotes, documents, "
                    "official findings, discoveries, timelines, or events. If a detail is "
                    "uncertain, phrase it as uncertain or omit it. If a famous legend "
                    "detail is disputed, exaggerated, or from later retellings, label it "
                    "that way or avoid it. Do not use fake expert interviews or imply "
                    "interviews or sources exist unless actual named sources are available "
                    "in the provided topic context. Do not use phrases like experts say "
                    "unless the plan identifies what kind of evidence supports the point. "
                    "Do not use generic filler like expert opinions unless specific "
                    "evidence or inquiry records are being discussed. "
                    "Every episode must stay directly tied to the requested topic. Do not "
                    "borrow details from other famous mysteries. Do not insert ghost ship "
                    "details into lighthouse cases, and do not insert lighthouse details "
                    "into ship cases. Do not invent boats, ships, lifeboats, notes, "
                    "letters, documents, interviews, witnesses, artifacts, or official "
                    "findings unless the requested topic specifically supports them. If "
                    "you are unsure whether a detail belongs to this topic, omit it or "
                    "label it as disputed folklore. Do not use generic mystery tropes as "
                    "evidence. Do not use fake-source-adjacent language such as expert "
                    "commentary, experts say, official sentiment, recorded statements, "
                    "interviews, or testimonies unless actual named or known sources are "
                    "provided. Prefer safer phrasing such as later historians have argued, "
                    "some interpretations suggest, contemporary records are limited, later "
                    "accounts claim, or the evidence does not prove. evidence_focus must "
                    "contain only topic-relevant evidence. "
                    "Do not present supernatural, alien, or paranormal theories as serious "
                    "explanations unless the requested topic is explicitly a legend or myth. "
                    "For factual cases, supernatural theories may be mentioned only as "
                    "cultural folklore or myths, not credible explanations. Avoid graphic "
                    "gore. Avoid fictional horror framing unless the topic is clearly a "
                    "legend or myth. Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Create a complete {episodes}-episode series plan for: {topic}\n\n"
                    f"Audience: {audience_text}\n"
                    f"Target duration per episode: {target_duration_seconds} seconds\n\n"
                    "Return one JSON object with these top-level fields:\n"
                    "series_title, topic, audience, target_duration_seconds, "
                    "episode_count, tone, factual_guardrails, series_narrative_arc, "
                    "what_is_known, what_is_uncertain, what_not_to_claim, "
                    "source_sensitivity_notes, key_people_or_groups, timeline, "
                    "episode_plan.\n\n"
                    "series_narrative_arc is mandatory. In a few sentences, describe "
                    "where the mystery begins, how the story escalates, the central "
                    "tension, and what the finale resolves or leaves unknown. The whole "
                    "series should feel like one connected eerie, cinematic, factual, "
                    "curiosity-driven documentary arc, not separate school-report topics.\n\n"
                    "Mandatory top-level factual guardrail fields:\n"
                    "- what_is_known\n"
                    "- what_is_uncertain\n"
                    "- what_not_to_claim\n"
                    "These three fields are required exactly as named. They must be "
                    "top-level JSON keys. They must be strings or lists. Do not rename "
                    "them. Do not put them only inside factual_guardrails. Do not omit "
                    "them.\n\n"
                    "source_sensitivity_notes must describe facts that need careful "
                    "wording, claims often exaggerated in retellings, theories that should "
                    "be framed as speculation, and details that should not be overstated.\n\n"
                    "For historical mysteries, what_is_known, what_is_uncertain, and "
                    "what_not_to_claim are mandatory quality guardrails. Use them to "
                    "separate documented facts from speculation. Do not guess exact dates "
                    "or background details. For ship mysteries, do not invent launch, "
                    "build, rename, route, captain, crew, cargo, or discovery details. "
                    "If the topic is Mary Celeste, the factual background is that the "
                    "ship was built/launched in 1861 as the Amazon and later renamed "
                    "Mary Celeste; do not claim it launched in 1830.\n\n"
                    "Topic-containment warning examples:\n"
                    "- For Flannan Isles, do not invent an empty ship, drifting vessel, "
                    "lifeboat, driftwood boat, or cryptic notes.\n"
                    "- For Mary Celeste, do not invent lighthouse logs or lighthouse keepers.\n"
                    "- For Roanoke, do not invent shipboard evidence or lighthouse evidence.\n"
                    "These examples are guardrails only; apply the same containment rule "
                    "to any requested topic.\n\n"
                    "episode_plan must be a list with exactly the requested number of "
                    "episode objects. If episodes=5, episode_plan must contain exactly "
                    "5 objects. Episode numbers must be sequential from 1 to the requested "
                    "episode count. Do not end the series before the requested episode "
                    "count. Do not describe Episode 4 as the final episode if episodes=5. "
                    "The final, legacy, or wrap-up episode must always be the last "
                    "requested episode number. Each episode object must include: episode_number, "
                    "title, episode_topic, story_job, hook, chapter_summary, key_beats, "
                    "continuity_from_previous, ending_tease, next_episode_setup, "
                    "suggested_template, suggested_image_count, suggested_thumbnail_angle, "
                    "suggested_video_format, evidence_focus, avoid_repeating. The final "
                    "episode must also include final_closing_thought.\n\n"
                    "evidence_focus must be a list of concrete evidence, known facts, "
                    "documents, locations, artifacts, or observations the episode should "
                    "use. Make entries specific to the topic, such as city council response, "
                    "contemporary chronicle accounts, carefully qualified reported numbers, "
                    "religious beliefs around St. Vitus, famine, disease, or social stress "
                    "context, later summaries of physician recommendations clearly framed, "
                    "disputed reports about dancer numbers and outcomes, later retellings "
                    "versus documented claims, last log entry, cargo condition, official "
                    "inquiry, weather reports, witness report, location of discovery, or "
                    "timeline gap. If there is no concrete evidence, say the episode is "
                    "interpretive or reflective and identify what it should avoid "
                    "overstating. Do not list generic or fake-source evidence such as "
                    "scholarly articles, expert opinions, psychological studies, interviews, "
                    "expert commentary, modern theories, personal accounts, official sentiment, "
                    "letters, documents, historical sources, historical documents, medical "
                    "records, unnamed sources, cryptic notes, empty ships, drifting vessels, "
                    "or lifeboats unless they are specifically "
                    "supported by the requested topic; if they are only legend material, "
                    "label them as disputed folklore. avoid_repeating must list specific "
                    "things this episode should not repeat from earlier episodes, such as "
                    "Do not re-explain the first dancer except in one sentence, Do not "
                    "repeat the full city background from Episode 2, or Do not treat "
                    "disputed death counts as established fact.\n\n"
                    "Episode planning style:\n"
                    "- Every episode must have a distinct story_job, reveal something new, "
                    "avoid repeating prior episodes, and end with a specific reason to continue.\n"
                    "- The whole series must feel like a connected story arc with escalating "
                    "questions, not a list of interchangeable topics.\n"
                    "- For a 5-episode factual mystery, prefer this structure unless the "
                    "topic demands otherwise: Episode 1 strongest hook and central mystery, "
                    "so the viewer understands why the story matters; Episode 2 pressure, "
                    "backstory, timeline, and context focused on the conditions that made "
                    "the mystery possible, not a dry history dump; Episode 3 strongest "
                    "evidence, contradictions, documents, clues, or witness accounts, "
                    "carefully separating known facts from later retellings; Episode 4 "
                    "theories, what each theory explains, and what each theory fails to "
                    "explain, with no theory presented as proven unless it is established; "
                    "Episode 5 legacy, most likely explanation if appropriate, and what "
                    "remains unknown, with an emotionally satisfying but careful ending.\n"
                    "- Episode titles must be specific, clickable, factual, dramatic without "
                    "overclaiming, different from each other, and tied to the episode's unique job.\n"
                    "- If the topic is about a lighthouse, titles must not reference ships "
                    "unless the actual topic includes a ship. If the topic is about a ship, "
                    "titles must not reference lighthouses unless the actual topic includes "
                    "a lighthouse.\n"
                    "- Avoid generic titles like The Beginning, The Evidence, The Theories, "
                    "The Legacy, Life Before the Mystery, What Happened, The Clues, The "
                    "Enduring Mystery, or Life Aboard.\n"
                    "- Avoid sensational titles that overstate uncertainty, such as Dancing "
                    "Until Dead, The Killer Dance, Everyone Died Dancing, or The Curse "
                    "That Killed Them.\n"
                    "- Prefer concrete titles like The Town That Couldn't Stop Moving, The "
                    "City Under Pressure, What the Records Actually Say, The Theory That "
                    "Almost Fits, What Still Doesn't Add Up, The Lighthouse Went Silent, "
                    "The Last Logbook, or The Search That Found Nothing, but do not overclaim.\n"
                    "- Hooks must be one or two strong sentences that open with a concrete, "
                    "scene-based image, contradiction, discovery, or eerie fact. Bad hook: "
                    "Imagine a town where people suddenly can't stop dancing. Better hook: "
                    "In the summer of 1518, a woman stepped into a Strasbourg street and "
                    "began to dance. Days later, she still had not stopped, and others "
                    "were joining her. Avoid generic questions, This episode explores, "
                    "In this episode we will, What really happened, The mystery remains, "
                    "or Why does this still haunt history.\n"
                    "- Episode 1 must begin with the strongest mystery hook, not slow background.\n"
                    "- Each episode must have a clear mini-arc: hook, setup, escalation, "
                    "reveal or turn, ending tease.\n"
                    "- Avoid generic phrases and awkward wording such as capturing event.\n"
                    "- Avoid risky overstatements such as perfect condition unless the "
                    "available evidence supports that exact wording.\n"
                    "- Do not use phrases like perfectly untouched, no one can explain, "
                    "or experts agree unless carefully qualified. Prefer careful wording "
                    "such as no obvious signs of violence, later retellings exaggerated "
                    "this detail, one possible explanation, or the official record does "
                    "not prove.\n"
                    "- Avoid repeating previous episodes.\n"
                    "- Each episode should naturally set up the next.\n"
                    "- Chapter summaries must be 150-240 words each, with no markdown "
                    "inside JSON. They must be detailed source material, not final narration "
                    "scripts. Include a strong opening situation, the episode's main question, "
                    "what evidence or context the episode uses, how the story escalates, "
                    "what the viewer learns, and how the episode connects to the next. "
                    "Avoid academic phrasing like This episode investigates, Viewers will "
                    "learn, This episode discusses, or explores various factors. Prefer "
                    "story-forward phrasing like The episode opens in, The tension builds "
                    "when, The key turn comes when, and By the end, the viewer understands.\n"
                    "- key_beats must include 6-9 specific scene-like story beats per episode. "
                    "Avoid generic beats like Introduction, Discussion, Expert analysis, "
                    "Historical context, Final thoughts, Compare theories, discussion of, "
                    "examination of, reflection on, modern theories of, contemporary society, "
                    "or expert commentary. Use concrete beats that can become scenes, such "
                    "as The records narrow the story but refuse to close it, The most famous "
                    "theory explains the pressure but not the first spark, Later folklore "
                    "turns a civic crisis into a legend, or The final question shifts from "
                    "what happened to why this story survived.\n"
                    "- ending_tease must set up the next episode specifically. Avoid vague "
                    "teases like What happened next, The mystery continues, More questions "
                    "remain, The legend continues, or The mystery remains. Do not use "
                    "unsupported claims such as cryptic notes unless the "
                    "episode establishes them as real or disputed. Prefer concrete teases "
                    "such as But the city's response may have turned a strange outbreak into "
                    "something even harder to control, Before we can judge the theories, we "
                    "have to ask what the records actually say and what they leave out, or "
                    "The most famous explanation sounds convincing at first, until one detail "
                    "gets in the way.\n"
                    "- The final episode does not need a next_episode_setup. Its ending_tease "
                    "may be empty or null. But it must include final_closing_thought: one "
                    "memorable, factual, eerie closing idea that names the unresolved core "
                    "tension. Bad finale: The mystery continues to fascinate people today. "
                    "Better finale: The records can tell us what Strasbourg feared. They "
                    "still cannot tell us exactly what made the dancing begin.\n"
                    "- The final episode must summarize what is known, identify the strongest "
                    "explanation if appropriate, explain what remains unknown, avoid repeating "
                    "all prior theories, avoid broad generic sociology language unless tied "
                    "directly to the story, and end with a memorable factual line.\n"
                    "- The final episode must not end vaguely with The mystery remains, The "
                    "legend continues, We may never know, or The story still fascinates us "
                    "today. It must identify the core unresolved tension, such as what the "
                    "records can show versus what they cannot explain.\n"
                    "- next_episode_setup must clearly name what the next episode investigates.\n\n"
                    "Factual caution must preserve drama without overclaiming. Avoid "
                    "overstating deaths, causes, motives, official findings, or exact numbers "
                    "when uncertain. Label disputed details as disputed. Use careful phrases "
                    "such as some accounts claim, later retellings suggest, records are "
                    "limited, historians still debate, one possible explanation, or the "
                    "evidence does not prove. Avoid bad phrasing such as records prove, "
                    "experts confirmed, everyone knew, the real cause was, or the truth is.\n\n"
                    "suggested_template must be exactly one of: default, bold, minimal, ai. "
                    "Use ai or bold for most mystery/history episodes. Do not output custom "
                    "template names such as mystery_build-up or tension_build-up. "
                    "Use suggested_image_count as an integer, usually 12 for 2-3 minute "
                    "episodes. Use suggested_video_format as landscape unless there is a "
                    "clear reason to use vertical."
                ),
            },
        ],
    )

    content = response.choices[0].message.content
    series_plan = _extract_json(content)
    series_plan = _normalize_series_plan(
        series_plan,
        topic=topic,
        episodes=episodes,
        target_duration_seconds=target_duration_seconds,
        audience=audience_text,
    )
    _validate_series_plan(series_plan, expected_episodes=episodes)
    return series_plan


def _unique_series_folder(series_title, output_name=None):
    base_slug = _safe_slug(output_name or series_title)
    folder = SERIES_OUTPUT_DIR / base_slug

    if not folder.exists():
        return folder

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return SERIES_OUTPUT_DIR / f"{base_slug}-{timestamp}"


def _write_full_story(series_plan, full_story_path):
    lines = [
        f"# {series_plan['series_title']}",
        "",
        f"Topic: {series_plan['topic']}",
        f"Audience: {series_plan['audience']}",
        f"Target duration: {series_plan['target_duration_seconds']} seconds",
        "",
        "## Series Narrative Arc",
        _markdown_list(series_plan.get("series_narrative_arc")),
        "",
        "## What Is Known",
        _markdown_list(series_plan.get("what_is_known")),
        "",
        "## What Is Uncertain",
        _markdown_list(series_plan.get("what_is_uncertain")),
        "",
        "## What Not To Claim",
        _markdown_list(series_plan.get("what_not_to_claim")),
        "",
        "## Source Sensitivity Notes",
        _markdown_list(series_plan.get("source_sensitivity_notes")),
        "",
        "## Timeline",
        _markdown_list(series_plan.get("timeline")),
        "",
        "## Episodes",
    ]

    for episode in series_plan["episode_plan"]:
        lines.extend(
            [
                "",
                f"### Episode {int(episode['episode_number']):02d}: {episode['title']}",
                "",
                f"Story job: {episode.get('story_job', '')}",
                "",
                str(episode.get("chapter_summary", "")).strip(),
                "",
                "Key beats:",
                _markdown_list(episode.get("key_beats")),
                "",
                "Evidence focus:",
                _markdown_list(episode.get("evidence_focus")),
                "",
                "Avoid repeating:",
                _markdown_list(episode.get("avoid_repeating")),
                "",
                f"Ending tease: {episode.get('ending_tease', '')}",
                "",
                f"Final closing thought: {episode.get('final_closing_thought', '')}",
            ]
        )

    full_story_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _markdown_list(value):
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, dict):
        return "\n".join(f"- {key}: {item}" for key, item in value.items())
    return str(value or "").strip()


def _write_chapter(series_plan, episode, chapter_path):
    episode_number = int(episode["episode_number"])
    lines = [
        f"# Episode {episode_number:02d}: {episode['title']}",
        "",
        f"Series: {series_plan['series_title']}",
        f"Episode topic: {episode['episode_topic']}",
        "",
        "## Story Job",
        str(episode.get("story_job", "")).strip(),
        "",
        "## Hook",
        str(episode.get("hook", "")).strip(),
        "",
        "## Chapter Summary",
        str(episode.get("chapter_summary", "")).strip(),
        "",
        "## Key Beats",
        _markdown_list(episode.get("key_beats")),
        "",
        "## Evidence Focus",
        _markdown_list(episode.get("evidence_focus")),
        "",
        "## Avoid Repeating",
        _markdown_list(episode.get("avoid_repeating")),
        "",
        "## Continuity From Previous",
        str(episode.get("continuity_from_previous", "")).strip(),
        "",
        "## Ending Tease",
        str(episode.get("ending_tease", "")).strip(),
        "",
        "## Next Episode Setup",
        str(episode.get("next_episode_setup", "")).strip(),
        "",
        "## Final Closing Thought",
        str(episode.get("final_closing_thought", "")).strip(),
        "",
        "## Factual Guardrails",
        _markdown_list(series_plan.get("factual_guardrails")),
        "",
        "## Source Sensitivity Notes",
        _markdown_list(series_plan.get("source_sensitivity_notes")),
        "",
        "## What Not To Claim",
        _markdown_list(series_plan.get("what_not_to_claim")),
    ]

    chapter_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def save_series_plan(series_plan, output_name=None):
    series_plan = _normalize_series_plan(series_plan)
    expected_episodes = _parse_positive_int(series_plan.get("episode_count"))
    _validate_series_plan(series_plan, expected_episodes=expected_episodes)
    SERIES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    series_folder = _unique_series_folder(series_plan["series_title"], output_name)
    chapters_folder = series_folder / "chapters"
    episodes_folder = series_folder / "episodes"
    chapters_folder.mkdir(parents=True, exist_ok=True)
    episodes_folder.mkdir(parents=True, exist_ok=True)

    series_bible_path = series_folder / "series_bible.json"
    episode_plan_path = series_folder / "episode_plan.json"
    full_story_path = series_folder / "full_story.md"

    series_bible = {
        key: value for key, value in series_plan.items() if key != "episode_plan"
    }

    series_bible_path.write_text(
        json.dumps(series_bible, indent=2) + "\n",
        encoding="utf-8",
    )
    episode_plan_path.write_text(
        json.dumps(series_plan["episode_plan"], indent=2) + "\n",
        encoding="utf-8",
    )
    _write_full_story(series_plan, full_story_path)

    chapter_paths = []
    for episode in series_plan["episode_plan"]:
        chapter_path = chapters_folder / _episode_filename(episode["episode_number"])
        _write_chapter(series_plan, episode, chapter_path)
        chapter_paths.append(str(chapter_path))

    return {
        "series_folder": str(series_folder),
        "series_bible_path": str(series_bible_path),
        "episode_plan_path": str(episode_plan_path),
        "full_story_path": str(full_story_path),
        "chapter_paths": chapter_paths,
    }


def load_series_plan(series_folder):
    series_path = Path(series_folder)
    series_bible_path = series_path / "series_bible.json"
    episode_plan_path = series_path / "episode_plan.json"

    return {
        "series_bible": json.loads(series_bible_path.read_text(encoding="utf-8")),
        "episode_plan": json.loads(episode_plan_path.read_text(encoding="utf-8")),
    }


def get_episode_source(series_folder, episode_number):
    loaded_plan = load_series_plan(series_folder)
    episode_number = int(episode_number)
    episode_plan = loaded_plan["episode_plan"]
    episode = next(
        (
            item
            for item in episode_plan
            if int(item.get("episode_number", -1)) == episode_number
        ),
        None,
    )

    if not episode:
        raise ValueError(f"Episode {episode_number} does not exist in the series plan")

    previous_episode = next(
        (
            item
            for item in episode_plan
            if int(item.get("episode_number", -1)) == episode_number - 1
        ),
        None,
    )
    next_episode = next(
        (
            item
            for item in episode_plan
            if int(item.get("episode_number", -1)) == episode_number + 1
        ),
        None,
    )

    chapter_path = Path(series_folder) / "chapters" / _episode_filename(episode_number)
    if not chapter_path.exists():
        raise FileNotFoundError(f"Episode chapter file does not exist: {chapter_path}")

    return {
        "series_folder": str(series_folder),
        "episode_number": episode_number,
        "chapter_text": chapter_path.read_text(encoding="utf-8"),
        "episode_plan": episode,
        "previous_episode": previous_episode,
        "next_episode": next_episode,
        "series_bible": loaded_plan["series_bible"],
    }
