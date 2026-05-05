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


def _validate_series_plan(series_plan):
    required_fields = [
        "series_title",
        "topic",
        "audience",
        "target_duration_seconds",
        "episode_count",
        "tone",
        "factual_guardrails",
        "what_is_known",
        "what_is_uncertain",
        "what_not_to_claim",
        "source_sensitivity_notes",
        "key_people_or_groups",
        "timeline",
        "episode_plan",
    ]

    missing = [field for field in required_fields if field not in series_plan]
    if missing:
        raise ValueError(f"Series plan is missing required fields: {', '.join(missing)}")

    episode_plan = series_plan.get("episode_plan")
    if not isinstance(episode_plan, list) or not episode_plan:
        raise ValueError("Series plan episode_plan must be a non-empty list")

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


def _normalize_series_plan(series_plan):
    series_plan.setdefault(
        "source_sensitivity_notes",
        [
            "Review dates, names, locations, evidence descriptions, and theories before production.",
        ],
    )
    return _normalize_episode_defaults(series_plan)


def _normalize_episode_defaults(series_plan):
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

    audience_text = audience or "fans of weird history, mysteries, and eerie factual stories"
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
                    "episode_count, tone, factual_guardrails, what_is_known, "
                    "what_is_uncertain, what_not_to_claim, source_sensitivity_notes, "
                    "key_people_or_groups, timeline, episode_plan.\n\n"
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
                    "episode_plan must be a list with exactly the requested number of "
                    "episode objects. Each episode object must include: episode_number, "
                    "title, episode_topic, hook, chapter_summary, key_beats, "
                    "continuity_from_previous, ending_tease, next_episode_setup, "
                    "suggested_template, suggested_image_count, suggested_thumbnail_angle, "
                    "suggested_video_format, evidence_focus, avoid_repeating.\n\n"
                    "evidence_focus must be a list of concrete evidence, known facts, "
                    "documents, locations, artifacts, or observations the episode should "
                    "use, such as last log entry, missing boat, cargo condition, official "
                    "inquiry, weather reports, witness report, location of discovery, or "
                    "timeline gap. If there is no concrete evidence, say the episode is "
                    "interpretive or reflective and identify what it should avoid "
                    "overstating. avoid_repeating must list what this episode should not "
                    "repeat from earlier episodes.\n\n"
                    "Episode planning style:\n"
                    "- Every episode must have a distinct job in the series.\n"
                    "- For a 5-episode factual mystery, prefer this structure unless the "
                    "topic demands otherwise: Episode 1 strongest hook/discovery/central "
                    "mystery; Episode 2 backstory and timeline leading up to the mystery; "
                    "Episode 3 main evidence and contradictions; Episode 4 theories and "
                    "what each theory fails to explain; Episode 5 legacy, most likely "
                    "explanation, and what remains unknown.\n"
                    "- Episode titles must be specific, clickable, and grounded in the case.\n"
                    "- Avoid generic titles like The Theories, The Clues, The Enduring "
                    "Mystery, or Life Aboard.\n"
                    "- Prefer concrete titles like The Lighthouse Went Silent, The Last "
                    "Logbook, The Empty Ship Found Drifting, The Search That Found Nothing, "
                    "or The Theory That Almost Fits, but do not overclaim.\n"
                    "- Hooks must be one or two strong sentences that open with a concrete "
                    "mystery, fact, clue, contradiction, or disappearance. Avoid generic "
                    "hooks like What happened, The mystery remains, or Why does this still "
                    "haunt history.\n"
                    "- Episode 1 must begin with the strongest mystery hook, not slow background.\n"
                    "- Each episode must have a clear mini-arc: hook, setup, escalation, "
                    "reveal or turn, ending tease.\n"
                    "- Avoid generic phrases and awkward wording such as capturing event.\n"
                    "- Avoid risky overstatements such as perfect condition unless the "
                    "available evidence supports that exact wording.\n"
                    "- Avoid repeating previous episodes.\n"
                    "- Each episode should naturally set up the next.\n"
                    "- Chapter summaries must be 120-220 words each, with no markdown "
                    "inside JSON. They must be detailed source material, not final narration "
                    "scripts. Include the episode mini-arc, what the viewer learns, concrete "
                    "facts, uncertainties, turning points, what not to overclaim, and how "
                    "the episode connects to the next.\n"
                    "- key_beats must include 5-8 specific beats per episode. Avoid generic "
                    "beats like Introduction, Discussion, Expert analysis, or Final thoughts. "
                    "Use concrete beats that can become scenes.\n"
                    "- ending_tease must set up the next episode specifically. Avoid vague "
                    "teases like The legend continues, The mystery remains, or What happened "
                    "next. Prefer concrete teases such as But the strangest clue was not what "
                    "was missing - it was what was written in the final log, or The search "
                    "should have answered everything. Instead, it made the timeline harder "
                    "to explain.\n"
                    "- next_episode_setup must clearly name what the next episode investigates.\n\n"
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
    series_plan = _normalize_series_plan(series_plan)
    _validate_series_plan(series_plan)
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
    _validate_series_plan(series_plan)
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
