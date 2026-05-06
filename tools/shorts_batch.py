import json
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from agents.script_agent import generate_short_script
from tools.generation_pipeline import run_full_generation_pipeline
from tools.text_cleaner import clean_narration_text, ensure_call_to_action
from tools.topic_research import research_topics
from tools.youtube_api import upload_video_from_run_folder


DAILY_BATCHES_OUTPUT_DIR = Path("outputs/daily_batches")
DEFAULT_NICHE = "weird history and strange true stories"
DEFAULT_AUDIENCE = "fans of weird history, mysteries, and eerie true stories"
DEFAULT_TARGET_DURATION_SECONDS = 45
DEFAULT_IMAGE_COUNT = 5
GENERIC_TOPICS = {
    "weird history",
    "weird history facts",
    "unsolved mysteries",
    "dark history",
    "scary history",
    "strange history",
    "mystery stories",
    "true stories",
}
CTA_PATTERN = re.compile(
    r"\b("
    r"subscribe|like this video|like and subscribe|follow|comment below|"
    r"share your thoughts|for more stories|for more mysteries|"
    r"for more strange history|if you want more|hit subscribe"
    r")\b",
    flags=re.IGNORECASE,
)
HOOK_PATTERN = re.compile(
    r"\b("
    r"strange|mystery|mysterious|vanished|disappeared|lost|found|"
    r"unknown|unexplained|forbidden|secret|clue|haunting|bizarre|"
    r"impossible|terrifying|why|how|what|no one|never returned"
    r")\b",
    flags=re.IGNORECASE,
)
OLD_CTA_PATTERN = re.compile(
    r"\b("
    r"ai business|artificial intelligence business|make money|side hustle|"
    r"passive income|earn money|financial freedom"
    r")\b",
    flags=re.IGNORECASE,
)
PRODUCTION_MARKUP_PATTERN = re.compile(
    r"(?im)("
    r"^\s*(narrator|host|voiceover|vo)\s*:|"
    r"\[\s*\d{1,2}:\d{2}|"
    r"^\s*(scene|camera|b-roll|music|sfx|cut to)\b|"
    r"[\[(]\s*(scene|camera|b-roll|music|sfx|cut to)[^\]\)]*[\])]|"
    r"\*\*[^*]+\*\*"
    r")"
)


def _slugify(value, fallback="batch", max_length=36):
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    slug = slug[:max_length].strip("-")
    return slug or fallback


def _next_batch_folder(niche):
    DAILY_BATCHES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    niche_slug = _slugify(niche, fallback="shorts")

    for index in range(1, 1000):
        batch_id = f"{date_prefix}-{niche_slug}-{index:03d}"
        batch_folder = DAILY_BATCHES_OUTPUT_DIR / batch_id

        if not batch_folder.exists():
            batch_folder.mkdir(parents=True, exist_ok=False)
            return batch_folder

    raise RuntimeError("Could not create a unique daily Shorts batch folder")


def _normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _word_count(text):
    return len(re.findall(r"\b[\w'-]+\b", str(text)))


def _sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", str(text).strip())
        if sentence.strip()
    ]


def _is_generic_text(value):
    normalized = _normalize_text(value).lower().strip(" .!?")
    if normalized in GENERIC_TOPICS:
        return True

    words = re.findall(r"[a-z0-9]+", normalized)
    return len(words) <= 2 and any(word in {"history", "mystery"} for word in words)


def _has_strong_hook(script):
    first_sentence = (_sentences(script) or [""])[0]
    return bool(first_sentence and _word_count(first_sentence) <= 35 and HOOK_PATTERN.search(first_sentence))


def _cta_sentence_count(script):
    return sum(1 for sentence in _sentences(script) if CTA_PATTERN.search(sentence))


def _load_metadata(metadata):
    if isinstance(metadata, dict):
        return metadata

    if metadata:
        metadata_path = Path(metadata)
        if metadata_path.exists():
            return json.loads(metadata_path.read_text(encoding="utf-8"))

    return {}


def _output_path(outputs, filename, output_key=None):
    run_folder = outputs.get("run_folder") if isinstance(outputs, dict) else None

    if run_folder:
        return Path(run_folder) / filename

    if output_key and isinstance(outputs, dict) and outputs.get(output_key):
        return Path(outputs[output_key])

    return None


def score_short_quality(
    topic,
    script,
    metadata,
    outputs,
    require_thumbnail=True,
):
    """
    Score a generated Short package with local checks only.
    """
    metadata = _load_metadata(metadata)
    outputs = outputs or {}
    script = _normalize_text(script)
    checks = []
    warnings = []
    score = 100
    missing_required_files = []

    def add_check(name, passed, warning, penalty=0, required=False, details=None):
        nonlocal score
        check = {
            "name": name,
            "passed": bool(passed),
            "penalty": 0 if passed else penalty,
        }

        if details is not None:
            check["details"] = details

        checks.append(check)

        if passed:
            return

        score -= penalty
        warnings.append(warning)

        if required:
            missing_required_files.append(name)

    words = _word_count(script)
    cta_count = _cta_sentence_count(script)
    title = _normalize_text(metadata.get("title"))

    add_check(
        "script_is_not_empty",
        bool(script),
        "Script is empty.",
        penalty=30,
        required=True,
    )
    add_check(
        "script_starts_with_strong_hook",
        _has_strong_hook(script),
        "Script may not start with a strong hook.",
        penalty=10,
    )
    add_check(
        "script_word_count_within_shorts_range",
        80 <= words <= 130,
        f"Script word count is {words}; ideal Shorts range is 80-130 words.",
        penalty=12 if 70 <= words <= 150 else 22,
        details={"word_count": words, "ideal_min": 80, "ideal_max": 130},
    )
    add_check(
        "script_has_no_duplicate_cta",
        cta_count <= 1,
        f"Script appears to contain {cta_count} CTA sentences.",
        penalty=14,
        details={"cta_sentence_count": cta_count},
    )
    add_check(
        "metadata_title_is_not_empty",
        bool(title),
        "Metadata title is empty.",
        penalty=18,
        required=True,
    )
    add_check(
        "title_is_not_too_generic",
        bool(title) and not _is_generic_text(title),
        "Metadata title is too generic.",
        penalty=12,
    )
    add_check(
        "topic_is_not_too_generic",
        not _is_generic_text(topic),
        "Topic is too generic.",
        penalty=12,
    )
    add_check(
        "no_old_ai_or_make_money_cta",
        not OLD_CTA_PATTERN.search(script),
        "Script appears to include an old AI or make-money CTA.",
        penalty=18,
    )
    add_check(
        "no_obvious_production_markup",
        not PRODUCTION_MARKUP_PATTERN.search(script),
        "Script appears to include production markup.",
        penalty=18,
    )

    required_files = {
        "video.mp4": "video",
        "audio.mp3": "audio",
        "captions.srt": "captions",
        "metadata.json": "metadata",
        "script.txt": "script",
    }

    for filename, output_key in required_files.items():
        file_path = _output_path(outputs, filename, output_key=output_key)
        exists = bool(file_path and file_path.exists() and file_path.stat().st_size > 0)
        add_check(
            f"{filename}_exists",
            exists,
            f"Required asset is missing or empty: {filename}",
            penalty=25,
            required=True,
            details={"path": str(file_path) if file_path else None},
        )

    thumbnail_path = _output_path(outputs, "thumbnail.png", output_key="thumbnail")
    thumbnail_exists = bool(
        thumbnail_path and thumbnail_path.exists() and thumbnail_path.stat().st_size > 0
    )
    add_check(
        "thumbnail.png_exists_if_enabled",
        thumbnail_exists if require_thumbnail else True,
        "Thumbnail generation is enabled, but thumbnail.png is missing or empty.",
        penalty=12,
        required=require_thumbnail,
        details={"path": str(thumbnail_path) if thumbnail_path else None},
    )

    score = max(0, score)
    passed = score >= 75 and not missing_required_files

    return {
        "topic": topic,
        "score": score,
        "passed": passed,
        "warnings": warnings,
        "checks": checks,
    }


def _topic_records(niche, audience, count):
    researched_topics = research_topics(niche=niche, audience=audience, count=count)
    topic_records = []
    seen = set()

    for item in researched_topics:
        topic = _normalize_text(item.get("topic") if isinstance(item, dict) else item)
        topic_key = topic.lower()

        if not topic or topic_key in seen:
            continue

        seen.add(topic_key)
        topic_records.append(item if isinstance(item, dict) else {"topic": topic})

        if len(topic_records) == count:
            break

    if len(topic_records) < count:
        raise RuntimeError(
            f"Topic research returned {len(topic_records)} unique topics, "
            f"but {count} were requested."
        )

    return topic_records


def _metadata_from_short_folder(short_folder):
    metadata_path = short_folder / "metadata.json"

    if not metadata_path.exists():
        return {}

    return json.loads(metadata_path.read_text(encoding="utf-8"))


def _recommended_action(quality_result, upload_ready, error=None):
    failed_checks = {
        check["name"]
        for check in quality_result.get("checks", [])
        if not check.get("passed")
    }

    if error:
        if any(name.endswith("_exists") for name in failed_checks):
            return "missing_required_asset"
        return "review_before_upload"

    if any(name.endswith("_exists") for name in failed_checks):
        return "missing_required_asset"

    if {
        "script_is_not_empty",
        "script_word_count_within_shorts_range",
        "script_has_no_duplicate_cta",
        "no_old_ai_or_make_money_cta",
        "no_obvious_production_markup",
    } & failed_checks:
        return "regenerate_script"

    if not quality_result.get("passed"):
        return "failed_quality_check"

    if upload_ready is not True:
        return "review_before_upload"

    return "ready_for_private_upload"


def _write_quality_score(short_folder, quality_result):
    quality_path = short_folder / "quality_score.json"
    quality_path.write_text(json.dumps(quality_result, indent=2) + "\n", encoding="utf-8")
    return str(quality_path)


def _write_next_steps(summary, next_steps_path):
    batch_folder = summary["batch_folder"]
    first_ready = next(
        (short for short in summary["shorts"] if short.get("passed")),
        summary["shorts"][0] if summary["shorts"] else None,
    )
    selected_folder = first_ready["folder"] if first_ready else f"{batch_folder}/short-01"
    upload_thumbnail_flag = " --upload-thumbnail" if summary["generate_thumbnail"] else ""

    content = f"""# Daily Shorts Batch Next Steps

Batch folder:

```bash
{batch_folder}
```

Generated {summary["count_completed"]} of {summary["count_requested"]} requested Shorts.
Quality passed: {summary["count_passed_quality"]}
Quality failed: {summary["count_failed_quality"]}

Open the batch folder on Mac:

```bash
open {batch_folder}
```

Upload-check a selected Short:

```bash
python main.py --mode upload-check --run-folder {selected_folder}
```

Privately upload one selected Short:

```bash
python main.py --mode upload --run-folder {selected_folder} --privacy-status private{upload_thumbnail_flag}
```

Review every video, title, description, captions, and thumbnail before publishing.
Public upload and publishing are manual for now.
"""

    next_steps_path.write_text(content, encoding="utf-8")
    return str(next_steps_path)


def _short_entry(
    short_number,
    topic,
    short_folder,
    metadata,
    quality_result,
    upload_ready,
    recommended_action,
    error=None,
):
    video_path = short_folder / "video.mp4"
    metadata_path = short_folder / "metadata.json"
    thumbnail_path = short_folder / "thumbnail.png"

    entry = {
        "short_number": short_number,
        "topic": topic,
        "title": metadata.get("title"),
        "folder": str(short_folder),
        "video_path": str(video_path) if video_path.exists() else None,
        "metadata_path": str(metadata_path) if metadata_path.exists() else None,
        "thumbnail_path": str(thumbnail_path) if thumbnail_path.exists() else None,
        "quality_score": quality_result.get("score"),
        "quality_score_path": str(short_folder / "quality_score.json"),
        "passed": quality_result.get("passed"),
        "warnings": quality_result.get("warnings", []),
        "upload_ready": upload_ready,
        "recommended_action": recommended_action,
    }

    if error:
        entry["error"] = error

    return entry


def create_daily_shorts_batch(
    niche=DEFAULT_NICHE,
    count=10,
    audience=DEFAULT_AUDIENCE,
    image_count=DEFAULT_IMAGE_COUNT,
    template="ai",
    generate_thumbnail=True,
    target_duration_seconds=DEFAULT_TARGET_DURATION_SECONDS,
    video_format="vertical",
    upload_ready_check=True,
):
    if count <= 0:
        raise ValueError("count must be greater than 0")

    if image_count <= 0:
        raise ValueError("image_count must be greater than 0")

    if target_duration_seconds <= 0:
        raise ValueError("target_duration_seconds must be greater than 0")

    if video_format not in {"vertical", "landscape"}:
        raise ValueError("video_format must be vertical or landscape")

    batch_folder = _next_batch_folder(niche)
    batch_id = batch_folder.name
    created_at = datetime.now().isoformat(timespec="seconds")
    topic_records = _topic_records(niche, audience, count)
    shorts = []

    for index, topic_record in enumerate(topic_records, start=1):
        topic = _normalize_text(topic_record["topic"])
        short_folder = batch_folder / f"short-{index:02d}"
        short_folder.mkdir(parents=True, exist_ok=True)
        upload_ready = None
        error = None

        try:
            script = generate_short_script(
                topic,
                target_duration_seconds=target_duration_seconds,
                niche=niche,
                audience=audience,
            )
            script = ensure_call_to_action(clean_narration_text(script))
            args = SimpleNamespace(
                use_ai_images=True,
                image_count=image_count,
                template=template,
                video_format=video_format,
                generate_thumbnail=generate_thumbnail,
                use_ai_thumbnail=False,
                caption_offset=0.2,
                words_per_caption=5,
                seconds_per_caption=1.6,
                organize=True,
                run_folder=str(short_folder),
                metadata_style="short",
                upload_ready_check=upload_ready_check,
            )
            outputs = run_full_generation_pipeline(topic, script, args)
            metadata = _metadata_from_short_folder(short_folder)
            upload_check_result = outputs.get("upload_check_result")
            upload_ready = (
                bool(upload_check_result.get("ready"))
                if upload_check_result is not None
                else None
            )
            quality_result = score_short_quality(
                topic,
                script,
                metadata,
                outputs,
                require_thumbnail=generate_thumbnail,
            )
        except Exception as exc:
            error = str(exc)
            outputs = {"run_folder": str(short_folder)}
            metadata = _metadata_from_short_folder(short_folder)
            quality_result = score_short_quality(
                topic,
                "",
                metadata,
                outputs,
                require_thumbnail=generate_thumbnail,
            )
            quality_result["warnings"].append(error)

        _write_quality_score(short_folder, quality_result)
        recommended_action = _recommended_action(
            quality_result,
            upload_ready,
            error=error,
        )
        shorts.append(
            _short_entry(
                index,
                topic,
                short_folder,
                metadata,
                quality_result,
                upload_ready,
                recommended_action,
                error=error,
            )
        )

    count_completed = sum(1 for short in shorts if short.get("video_path"))
    count_passed = sum(1 for short in shorts if short.get("passed"))
    summary = {
        "batch_id": batch_id,
        "batch_folder": str(batch_folder),
        "created_at": created_at,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "niche": niche,
        "audience": audience,
        "count_requested": count,
        "count_completed": count_completed,
        "count_passed_quality": count_passed,
        "count_failed_quality": count - count_passed,
        "image_count": image_count,
        "template": template,
        "generate_thumbnail": generate_thumbnail,
        "target_duration_seconds": target_duration_seconds,
        "video_format": video_format,
        "upload_ready_check": upload_ready_check,
        "shorts": shorts,
    }
    summary_path = batch_folder / "batch_summary.json"
    next_steps_path = batch_folder / "NEXT_STEPS.md"
    summary["batch_summary_path"] = str(summary_path)
    summary["next_steps_path"] = str(next_steps_path)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_next_steps(summary, next_steps_path)

    return summary


def upload_batch_private(batch_folder, limit=None, upload_thumbnail=False):
    batch_path = Path(batch_folder)
    summary_path = batch_path / "batch_summary.json"

    if not summary_path.exists():
        raise FileNotFoundError(f"batch_summary.json does not exist: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    eligible_shorts = [
        short
        for short in summary.get("shorts", [])
        if short.get("passed") and short.get("folder")
    ]

    if limit is not None:
        eligible_shorts = eligible_shorts[:limit]

    results = {
        "batch_folder": str(batch_path),
        "privacy_status": "private",
        "upload_thumbnail": upload_thumbnail,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "completed_at": None,
        "results": [],
    }

    for short in eligible_shorts:
        run_folder = short["folder"]
        result = {
            "short_number": short.get("short_number"),
            "topic": short.get("topic"),
            "run_folder": run_folder,
            "uploaded": False,
            "error": None,
        }

        try:
            upload_result = upload_video_from_run_folder(
                run_folder,
                privacy_status="private",
                upload_thumbnail=upload_thumbnail,
            )
            result.update(upload_result)
            result["uploaded"] = True
        except Exception as exc:
            result["error"] = str(exc)

        results["results"].append(result)

    results["completed_at"] = datetime.now().isoformat(timespec="seconds")
    results_path = batch_path / "upload_results.json"
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    results["upload_results_path"] = str(results_path)
    return results
