import argparse
import json
from datetime import datetime
from pathlib import Path

from agents.script_agent import generate_episode_script_from_chapter, generate_script
from tools.captions import save_srt_captions
from tools.file_writer import save_script
from tools.generation_pipeline import (
    get_audio_duration_seconds,
    run_full_generation_pipeline,
)
from tools.image_generator import generate_scene_images
from tools.image_inputs import collect_image_paths
from tools.logger import log_pipeline_run
from tools.metadata import save_video_metadata
from tools.run_folder import organize_run_outputs
from tools.series_planner import (
    create_series_plan,
    create_shorts_series_plan,
    get_episode_source,
    load_series_plan,
    save_series_plan,
    save_quality_report,
    series_plan_from_loaded,
)
from tools.test_audio import create_test_audio
from tools.text_cleaner import clean_narration_text, ensure_call_to_action
from tools.thumbnail_generator import generate_thumbnail
from tools.topic_research import research_topics, save_topic_research
from tools.upload_check import validate_upload_package
from tools.voiceover import generate_voiceover
from tools.video_builder import build_video
from tools.youtube_api import (
    upload_thumbnail_for_video,
    upload_video_from_run_folder,
)


DEFAULT_TOPIC = "The strangest disappearance in history"
DEFAULT_TARGET_DURATION_SECONDS = 150
DEFAULT_SHORTS_TARGET_DURATION_SECONDS = 75
DEFAULT_SHORTS_IMAGE_COUNT = 7
DEFAULT_CAPTION_OFFSET = 1.2
DEFAULT_WORDS_PER_CAPTION = 8
DEFAULT_SECONDS_PER_CAPTION = 2.5
BATCH_OUTPUT_DIR = Path("outputs/batches")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run specific parts of the RelayWorks AI Content Brain pipeline."
    )
    parser.add_argument(
        "--mode",
        choices=[
            "full",
            "script",
            "voiceover",
            "video",
            "test-audio",
            "captions",
            "metadata",
            "upload-check",
            "upload",
            "thumbnail",
            "topic-research",
            "series-plan",
            "series-check",
            "batch-series",
            "daily-shorts",
            "upload-batch-private",
            "shorts-series-private-upload",
        ],
        default="full",
        help="Pipeline mode to run.",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Topic to use for script generation or video title.",
    )
    parser.add_argument(
        "--target-duration-seconds",
        type=int,
        default=DEFAULT_TARGET_DURATION_SECONDS,
        help="Target spoken script duration in seconds for script and full modes.",
    )
    parser.add_argument(
        "--audio-path",
        help="Existing audio file path required when --mode video.",
    )
    parser.add_argument(
        "--captions-path",
        help="Optional SRT captions file path used when --mode video.",
    )
    parser.add_argument(
        "--images-dir",
        help="Optional directory of local images to use in generated videos.",
    )
    parser.add_argument(
        "--image-paths",
        nargs="+",
        help="Optional one or more local image paths to use in generated videos.",
    )
    parser.add_argument(
        "--template",
        default="default",
        help="Built-in local video template to use when generating videos.",
    )
    parser.add_argument(
        "--video-format",
        choices=["vertical", "landscape"],
        default="landscape",
        help=(
            "Video aspect format to render. Use landscape for episode videos "
            "or vertical for Shorts-style videos."
        ),
    )
    parser.add_argument(
        "--organize",
        action="store_true",
        help="Copy generated outputs into a timestamped local run folder.",
    )
    parser.add_argument(
        "--caption-offset",
        type=float,
        default=DEFAULT_CAPTION_OFFSET,
        help="Caption start offset in seconds used when full mode has audio duration.",
    )
    parser.add_argument(
        "--words-per-caption",
        type=int,
        default=DEFAULT_WORDS_PER_CAPTION,
        help="Number of words to include in each generated caption.",
    )
    parser.add_argument(
        "--seconds-per-caption",
        type=float,
        default=DEFAULT_SECONDS_PER_CAPTION,
        help="Caption duration in seconds when no audio duration is available.",
    )
    parser.add_argument(
        "--use-ai-images",
        action="store_true",
        help="Generate OpenAI scene images for full-mode videos.",
    )
    parser.add_argument(
        "--generate-thumbnail",
        action="store_true",
        help="Generate a local thumbnail during full mode.",
    )
    parser.add_argument(
        "--thumbnail-source",
        help="Optional local source image path for --mode thumbnail.",
    )
    parser.add_argument(
        "--use-ai-thumbnail",
        action="store_true",
        help="Generate a thumbnail background with OpenAI.",
    )
    parser.add_argument(
        "--image-count",
        type=int,
        default=5,
        help="Number of AI scene images to generate when --use-ai-images is set.",
    )
    parser.add_argument(
        "--run-folder",
        help="Organized run folder path required when --mode upload-check or --mode upload.",
    )
    parser.add_argument(
        "--privacy-status",
        help="YouTube privacy status for --mode upload: private, unlisted, or public.",
    )
    parser.add_argument(
        "--upload-thumbnail",
        action="store_true",
        help="Upload run-folder thumbnail.png after a successful YouTube video upload.",
    )
    parser.add_argument(
        "--niche",
        help="Niche to research when --mode topic-research or --mode daily-shorts.",
    )
    parser.add_argument(
        "--audience",
        help=(
            "Optional audience to target when --mode topic-research, "
            "--mode series-plan, or --mode daily-shorts."
        ),
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of Shorts to generate when --mode daily-shorts.",
    )
    parser.add_argument(
        "--short-image-count",
        type=int,
        default=5,
        help="Number of AI scene images per Short when --mode daily-shorts.",
    )
    parser.add_argument(
        "--short-duration-seconds",
        type=int,
        default=45,
        help="Target spoken duration per Short when --mode daily-shorts.",
    )
    parser.add_argument(
        "--no-thumbnail",
        action="store_true",
        help="Skip thumbnail generation when --mode daily-shorts.",
    )
    parser.add_argument(
        "--skip-upload-check",
        action="store_true",
        help="Skip local upload-check validation when --mode daily-shorts.",
    )
    parser.add_argument(
        "--ignore-topic-history",
        action="store_true",
        help=(
            "Allow daily-shorts to reuse topics by skipping local topic history checks."
        ),
    )
    parser.add_argument(
        "--topic-count",
        type=int,
        default=10,
        help="Number of topic ideas to generate when --mode topic-research.",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help=(
            "Number of episodes to plan when --mode series-plan, or first N "
            "episodes to use when supported by a series mode."
        ),
    )
    parser.add_argument(
        "--series-folder",
        help="Series folder path required when --mode series-check or --mode batch-series.",
    )
    parser.add_argument(
        "--episode",
        type=int,
        help="Single episode number to generate when --mode batch-series.",
    )
    parser.add_argument(
        "--episodes-range",
        help="Episode range to generate when --mode batch-series, for example 1-5.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help=(
            "Continue later Shorts when one fails in "
            "--mode shorts-series-private-upload."
        ),
    )
    parser.add_argument(
        "--force-batch",
        action="store_true",
        help=(
            "Allow batch-series to run even when quality_report.json is not ready."
        ),
    )
    parser.add_argument(
        "--batch-folder",
        help="Daily batch folder path required when --mode upload-batch-private.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of passed Shorts to upload when --mode upload-batch-private.",
    )
    return parser.parse_args()


def log_success(topic, mode, outputs, organize=False):
    log_outputs = dict(outputs)

    if organize:
        organize_result = organize_run_outputs(topic, outputs)
        log_outputs["run_folder"] = organize_result["run_folder"]
        log_outputs["copied_outputs"] = organize_result["copied_outputs"]

        print("\nOrganized run folder:")
        print(organize_result["run_folder"])

    log_entry = log_pipeline_run(topic, mode, log_outputs)

    print("\nLogged pipeline run:")
    print(log_entry)


def print_topic_research(topics, saved_path):
    print("\nTopic ideas:")
    for topic in topics:
        print(
            f"{topic['rank']}. {topic['topic']} "
            f"(viral {topic['viral_potential_score']}/10, "
            f"difficulty {topic['production_difficulty_score']}/10, "
            f"combined {topic['combined_score']})"
        )
        print(f"   Hook: {topic['hook']}")
        print(f"   Template: {topic['suggested_template']}")
        print(f"   Title: {topic['suggested_title']}")

    print("\nSaved topic research path:")
    print(saved_path)

    if topics:
        top_topic = topics[0]
        print("\nExample full-mode command from the top topic:")
        print(
            "python main.py --mode full "
            f"--topic {json.dumps(top_topic['topic'])} "
            f"--template {top_topic['suggested_template']} "
            "--organize --use-ai-images --image-count 3 --generate-thumbnail"
        )


def print_series_plan_result(saved_paths):
    print("\nSaved series folder:")
    print(saved_paths["series_folder"])
    print("\nSaved series bible path:")
    print(saved_paths["series_bible_path"])
    print("\nSaved episode plan path:")
    print(saved_paths["episode_plan_path"])
    print("\nSaved full story path:")
    print(saved_paths["full_story_path"])
    print("\nSaved quality report path:")
    print(saved_paths["quality_report_path"])
    print("\nSaved chapter paths:")
    for chapter_path in saved_paths["chapter_paths"]:
        print(chapter_path)


def _episode_title(episode_plan):
    return str(episode_plan.get("title") or episode_plan.get("episode_topic"))


def _episode_topic(series_bible, episode_plan):
    series_title = series_bible.get("series_title", series_bible.get("topic", "Series"))
    return (
        f"{series_title} Episode {int(episode_plan['episode_number'])}: "
        f"{_episode_title(episode_plan)}"
    )


def _parse_episodes_range(value):
    try:
        start_text, end_text = value.split("-", 1)
        start = int(start_text)
        end = int(end_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("--episodes-range must use the format START-END") from exc

    if start <= 0 or end <= 0:
        raise ValueError("--episodes-range values must be greater than 0")
    if start > end:
        raise ValueError("--episodes-range start must be less than or equal to end")

    return list(range(start, end + 1))


def _select_batch_episodes(args, episode_plan):
    if args.episode is not None and args.episodes_range:
        raise ValueError("Use either --episode or --episodes-range, not both")

    available_episodes = {
        int(episode["episode_number"]) for episode in episode_plan
    }

    if args.episode is not None:
        if args.episode <= 0:
            raise ValueError("--episode must be greater than 0")
        selected_episodes = [args.episode]
    elif args.episodes_range:
        selected_episodes = _parse_episodes_range(args.episodes_range)
    elif args.episodes is not None:
        if args.episodes <= 0:
            raise ValueError("--episodes must be greater than 0")
        selected_episodes = sorted(available_episodes)[: args.episodes]
        if len(selected_episodes) < args.episodes:
            raise ValueError(
                f"Series plan has {len(selected_episodes)} episodes, "
                f"but --episodes requested {args.episodes}"
            )
    else:
        selected_episodes = sorted(available_episodes)

    missing_episodes = [
        episode_number
        for episode_number in selected_episodes
        if episode_number not in available_episodes
    ]
    if missing_episodes:
        raise ValueError(
            "Requested episodes do not exist in the series plan: "
            + ", ".join(str(episode_number) for episode_number in missing_episodes)
        )

    return selected_episodes


def _write_batch_summary(summary, filename_kind="batch"):
    BATCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    series_slug = Path(summary["series_folder"]).name or "series"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary_path = BATCH_OUTPUT_DIR / f"{series_slug}-{filename_kind}-{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return str(summary_path)


def _write_episode_record(series_folder, episode_source, result, upload_result=None):
    episode_plan = episode_source["episode_plan"]
    episode_number = int(episode_plan["episode_number"])
    episodes_folder = Path(series_folder) / "episodes"
    episodes_folder.mkdir(parents=True, exist_ok=True)
    upload_result = upload_result or {}

    record = {
        "episode_number": episode_number,
        "title": _episode_title(episode_plan),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "chapter_path": str(
            Path(series_folder) / "chapters" / f"episode-{episode_number:02d}.md"
        ),
        "summary": episode_plan.get("chapter_summary"),
        "starts_from": episode_plan.get("continuity_from_previous"),
        "ends_with": episode_plan.get("ending_tease"),
        "next_episode_tease": episode_plan.get("next_episode_setup"),
        "run_folder": result.get("run_folder"),
        "upload_ready": bool(
            result.get("upload_check_result", {}).get("ready")
            if result.get("upload_check_result")
            else False
        ),
        "youtube_video_id": upload_result.get("video_id"),
        "youtube_video_url": upload_result.get("video_url"),
        "thumbnail_uploaded": bool(upload_result.get("thumbnail_uploaded")),
        "uploaded_at": upload_result.get("uploaded_at"),
        "video_format": result.get("video_format"),
        "target_duration_seconds": result.get("target_duration_seconds"),
    }

    if upload_result.get("thumbnail_error"):
        record["thumbnail_error"] = upload_result["thumbnail_error"]
    if result.get("error"):
        record["error"] = result["error"]

    record_path = episodes_folder / f"episode-{episode_number:02d}.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return str(record_path)


def run_private_upload_for_run_folder(run_folder, privacy_status="private"):
    upload_result = upload_video_from_run_folder(
        run_folder,
        privacy_status=privacy_status or "private",
        upload_thumbnail=False,
    )
    upload_result["thumbnail_uploaded"] = False
    upload_result["uploaded_at"] = datetime.now().isoformat(timespec="seconds")

    thumbnail_path = Path(run_folder) / "thumbnail.png"
    if not thumbnail_path.exists():
        return upload_result

    try:
        thumbnail_response = upload_thumbnail_for_video(
            upload_result["video_id"],
            thumbnail_path,
        )
        upload_result["thumbnail_uploaded"] = True
        upload_result["thumbnail_path"] = str(thumbnail_path)
        upload_result["thumbnail_response"] = thumbnail_response
    except Exception as exc:
        upload_result["thumbnail_error"] = str(exc)

    return upload_result


def run_batch_series(args):
    if not args.series_folder:
        raise ValueError("--series-folder is required when --mode batch-series")

    loaded_plan = load_series_plan(args.series_folder)
    series_plan = series_plan_from_loaded(loaded_plan)
    quality_report, quality_report_path = save_quality_report(
        series_plan,
        args.series_folder,
    )
    if not quality_report.get("ready_for_batch"):
        message = (
            "Series plan is not ready for batch-series. "
            f"Review {quality_report_path}. Issues: "
            + "; ".join(quality_report.get("issues", []))
        )
        if not args.force_batch:
            raise RuntimeError(message)

        print("\nWARNING: --force-batch used. Continuing despite quality issues.")
        print(message)

    selected_episodes = _select_batch_episodes(args, loaded_plan["episode_plan"])
    started_at = datetime.now().isoformat(timespec="seconds")
    summary = {
        "series_folder": args.series_folder,
        "started_at": started_at,
        "completed_at": None,
        "selected_episodes": selected_episodes,
        "successful_episodes": [],
        "failed_episode": None,
        "episode_results": [],
    }

    for episode_number in selected_episodes:
        try:
            episode_source = get_episode_source(args.series_folder, episode_number)
            episode_plan = episode_source["episode_plan"]
            topic = _episode_topic(episode_source["series_bible"], episode_plan)
            script = generate_episode_script_from_chapter(
                episode_source,
                target_duration_seconds=args.target_duration_seconds,
            )

            print(f"\nGenerated episode {episode_number} script:")
            print(script)

            outputs = run_full_generation_pipeline(topic, script, args)
            run_folder = outputs.get("run_folder")
            upload_check_result = outputs.get("upload_check_result")

            result = {
                "episode_number": episode_number,
                "episode_title": _episode_title(episode_plan),
                "script_path": outputs.get("script"),
                "captions_path": outputs.get("captions"),
                "metadata_path": outputs.get("metadata"),
                "audio_path": outputs.get("audio"),
                "video_path": outputs.get("video"),
                "thumbnail_path": outputs.get("thumbnail"),
                "run_folder": run_folder,
                "upload_check_result": upload_check_result,
                "video_format": args.video_format,
                "target_duration_seconds": args.target_duration_seconds,
            }
            result["episode_record_path"] = _write_episode_record(
                args.series_folder,
                episode_source,
                result,
            )

            summary["successful_episodes"].append(episode_number)
            summary["episode_results"].append(result)
        except Exception as exc:
            summary["failed_episode"] = episode_number
            summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
            summary_path = _write_batch_summary(summary)
            raise RuntimeError(
                f"Batch-series failed on episode {episode_number}. "
                f"Saved batch summary to {summary_path}. Original error: {exc}"
            ) from exc

    summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
    summary_path = _write_batch_summary(summary)

    print("\nSaved batch summary path:")
    print(summary_path)


def _configure_shorts_defaults(args):
    args.organize = True
    args.use_ai_images = True
    args.generate_thumbnail = True

    if args.template == "default":
        args.template = "ai"
    if args.image_count == 5:
        args.image_count = DEFAULT_SHORTS_IMAGE_COUNT
    if args.target_duration_seconds == DEFAULT_TARGET_DURATION_SECONDS:
        args.target_duration_seconds = DEFAULT_SHORTS_TARGET_DURATION_SECONDS
    if args.video_format == "landscape":
        args.video_format = "vertical"
    if not args.privacy_status:
        args.privacy_status = "private"


def _load_or_create_shorts_series(args):
    if args.series_folder:
        return args.series_folder

    if not args.topic:
        raise ValueError(
            "--topic is required when --mode shorts-series-private-upload "
            "unless --series-folder is provided"
        )

    series_plan = create_shorts_series_plan(
        topic=args.topic,
        episodes=args.episodes or 5,
        target_duration_seconds=args.target_duration_seconds,
        audience=args.audience,
    )
    saved_paths = save_series_plan(series_plan)
    print_series_plan_result(saved_paths)
    return saved_paths["series_folder"]


def _selected_shorts_episodes(series_folder, episode_count):
    loaded_plan = load_series_plan(series_folder)
    available_episodes = sorted(
        int(episode["episode_number"]) for episode in loaded_plan["episode_plan"]
    )
    selected_episodes = available_episodes[:episode_count]

    if len(selected_episodes) < episode_count:
        raise ValueError(
            f"Series folder has {len(selected_episodes)} episodes, "
            f"but --episodes requested {episode_count}"
        )

    return selected_episodes


def run_shorts_series_private_upload(args):
    _configure_shorts_defaults(args)
    episode_count = args.episodes or 5
    series_folder = _load_or_create_shorts_series(args)
    selected_episodes = _selected_shorts_episodes(series_folder, episode_count)
    loaded_plan = load_series_plan(series_folder)
    topic = args.topic or loaded_plan["series_bible"].get("topic")
    summary = {
        "mode": "shorts-series-private-upload",
        "topic": topic,
        "series_folder": series_folder,
        "episode_count": len(selected_episodes),
        "privacy_status": args.privacy_status,
        "video_format": args.video_format,
        "target_duration_seconds": args.target_duration_seconds,
        "image_count": args.image_count,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "completed_at": None,
        "stop_on_error": not args.continue_on_error,
        "episodes": [],
    }

    for episode_number in selected_episodes:
        episode_source = None
        episode_plan = None
        result = {
            "episode_number": episode_number,
            "title": None,
            "run_folder": None,
            "upload_ready": False,
            "video_id": None,
            "video_url": None,
            "thumbnail_uploaded": False,
            "errors": [],
        }

        try:
            episode_source = get_episode_source(series_folder, episode_number)
            episode_plan = episode_source["episode_plan"]
            result["title"] = _episode_title(episode_plan)
            episode_topic = _episode_topic(episode_source["series_bible"], episode_plan)
            script = generate_episode_script_from_chapter(
                episode_source,
                target_duration_seconds=args.target_duration_seconds,
            )

            print(f"\nGenerated Short {episode_number} script:")
            print(script)

            outputs = run_full_generation_pipeline(episode_topic, script, args)
            run_folder = outputs.get("run_folder")
            upload_check_result = outputs.get("upload_check_result")
            result["run_folder"] = run_folder
            result["upload_ready"] = bool(
                upload_check_result and upload_check_result.get("ready")
            )

            if not run_folder:
                raise RuntimeError("Short generation did not create an organized run folder")

            if not result["upload_ready"]:
                errors = (
                    upload_check_result.get("errors", [])
                    if upload_check_result
                    else ["Upload check did not run"]
                )
                print("\nUpload check failed:")
                print(json.dumps(upload_check_result, indent=2))
                raise RuntimeError("; ".join(errors))

            upload_result = run_private_upload_for_run_folder(
                run_folder,
                privacy_status=args.privacy_status,
            )
            result["video_id"] = upload_result.get("video_id")
            result["video_url"] = upload_result.get("video_url")
            result["thumbnail_uploaded"] = bool(upload_result.get("thumbnail_uploaded"))

            if upload_result.get("thumbnail_error"):
                result["errors"].append(
                    f"Thumbnail upload failed: {upload_result['thumbnail_error']}"
                )

            record_result = {
                "run_folder": run_folder,
                "upload_check_result": upload_check_result,
                "video_format": args.video_format,
                "target_duration_seconds": args.target_duration_seconds,
            }
            result["episode_record_path"] = _write_episode_record(
                series_folder,
                episode_source,
                record_result,
                upload_result=upload_result,
            )
        except Exception as exc:
            result["errors"].append(str(exc))

            if episode_source:
                record_result = {
                    "run_folder": result.get("run_folder"),
                    "upload_check_result": {
                        "ready": result.get("upload_ready", False),
                    },
                    "video_format": args.video_format,
                    "target_duration_seconds": args.target_duration_seconds,
                    "error": str(exc),
                }
                result["episode_record_path"] = _write_episode_record(
                    series_folder,
                    episode_source,
                    record_result,
                )

            summary["episodes"].append(result)
            if not args.continue_on_error:
                summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
                summary["summary_path"] = _write_batch_summary(
                    summary,
                    filename_kind="shorts-private-upload-summary",
                )
                print(json.dumps(summary, indent=2))
                raise RuntimeError(
                    f"Shorts private upload failed on episode {episode_number}. "
                    f"Saved summary to {summary['summary_path']}. Original error: {exc}"
                ) from exc
            continue

        summary["episodes"].append(result)

    summary["completed_at"] = datetime.now().isoformat(timespec="seconds")
    summary["summary_path"] = _write_batch_summary(
        summary,
        filename_kind="shorts-private-upload-summary",
    )

    print(json.dumps(summary, indent=2))


def run_series_check(args):
    if not args.series_folder:
        raise ValueError("--series-folder is required when --mode series-check")

    loaded_plan = load_series_plan(args.series_folder)
    quality_report, quality_report_path = save_quality_report(
        series_plan_from_loaded(loaded_plan),
        args.series_folder,
    )
    result = {
        **quality_report,
        "quality_report_path": quality_report_path,
    }
    print(json.dumps(result, indent=2))


def main():
    args = parse_args()
    topic = args.topic or DEFAULT_TOPIC
    image_paths = []

    if args.image_count <= 0:
        raise ValueError("--image-count must be greater than 0")

    if args.words_per_caption <= 0:
        raise ValueError("--words-per-caption must be greater than 0")

    if args.seconds_per_caption <= 0:
        raise ValueError("--seconds-per-caption must be greater than 0")

    if args.target_duration_seconds <= 0:
        raise ValueError("--target-duration-seconds must be greater than 0")

    if args.episodes is not None and args.episodes <= 0:
        raise ValueError("--episodes must be greater than 0")

    if args.count <= 0:
        raise ValueError("--count must be greater than 0")

    if args.short_image_count <= 0:
        raise ValueError("--short-image-count must be greater than 0")

    if args.short_duration_seconds <= 0:
        raise ValueError("--short-duration-seconds must be greater than 0")

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be greater than 0")

    if args.mode == "series-plan":
        if not args.topic:
            raise ValueError("--topic is required when --mode series-plan")

        series_plan = create_series_plan(
            topic=args.topic,
            episodes=args.episodes or 5,
            target_duration_seconds=args.target_duration_seconds,
            audience=args.audience,
        )
        saved_paths = save_series_plan(series_plan)
        print_series_plan_result(saved_paths)
        return

    if args.mode == "series-check":
        run_series_check(args)
        return

    if args.mode == "batch-series":
        run_batch_series(args)
        return

    if args.mode == "shorts-series-private-upload":
        run_shorts_series_private_upload(args)
        return

    if args.mode == "daily-shorts":
        from tools.shorts_batch import (
            DEFAULT_AUDIENCE,
            DEFAULT_NICHE,
            create_daily_shorts_batch,
        )

        summary = create_daily_shorts_batch(
            niche=args.niche or DEFAULT_NICHE,
            count=args.count,
            audience=args.audience or DEFAULT_AUDIENCE,
            image_count=args.short_image_count,
            template=args.template if args.template != "default" else "ai",
            generate_thumbnail=not args.no_thumbnail,
            target_duration_seconds=args.short_duration_seconds,
            video_format="vertical",
            upload_ready_check=not args.skip_upload_check,
            ignore_topic_history=args.ignore_topic_history,
        )

        print("\nDaily Shorts batch complete:")
        print(f"Batch folder: {summary['batch_folder']}")
        print(f"Completed: {summary['count_completed']}")
        print(f"Passed quality: {summary['count_passed_quality']}")
        print(f"Batch summary: {summary['batch_summary_path']}")
        print(f"Next steps: {summary['next_steps_path']}")
        return

    if args.mode == "upload-batch-private":
        if not args.batch_folder:
            raise ValueError("--batch-folder is required when --mode upload-batch-private")

        from tools.shorts_batch import upload_batch_private

        upload_results = upload_batch_private(
            args.batch_folder,
            limit=args.limit,
            upload_thumbnail=args.upload_thumbnail,
        )
        print(json.dumps(upload_results, indent=2))
        return

    if args.mode == "topic-research":
        if not args.niche:
            raise ValueError("--niche is required when --mode topic-research")
        if args.topic_count <= 0:
            raise ValueError("--topic-count must be greater than 0")

        topics = research_topics(
            niche=args.niche,
            audience=args.audience,
            count=args.topic_count,
        )
        saved_path = save_topic_research(args.niche, topics)
        print_topic_research(topics, saved_path)
        return

    if args.mode == "upload-check":
        if not args.run_folder:
            raise ValueError("--run-folder is required when --mode upload-check")

        validation_result = validate_upload_package(args.run_folder)
        print(json.dumps(validation_result, indent=2))
        return

    if args.mode == "upload":
        if not args.run_folder:
            raise ValueError("--run-folder is required when --mode upload")

        upload_result = upload_video_from_run_folder(
            args.run_folder,
            privacy_status=args.privacy_status,
            upload_thumbnail=args.upload_thumbnail,
        )
        print(json.dumps(upload_result, indent=2))
        return

    if args.mode == "thumbnail":
        thumbnail_source_paths = (
            [args.thumbnail_source] if args.thumbnail_source else None
        )
        thumbnail_path = generate_thumbnail(
            topic,
            topic,
            source_image_paths=thumbnail_source_paths,
            use_ai=args.use_ai_thumbnail,
            template=args.template,
        )

        print("\nSaved thumbnail path:")
        print(thumbnail_path)
        return

    if args.mode in ["full", "video"]:
        image_paths = collect_image_paths(args.images_dir, args.image_paths)

    if args.mode == "test-audio":
        audio_path = create_test_audio(topic)
        outputs = {"audio": audio_path}

        print("\nSaved audio path:")
        print(audio_path)

        log_success(topic, args.mode, outputs, args.organize)
        return

    if args.mode == "video":
        if not args.audio_path:
            raise ValueError("--audio-path is required when --mode video")

        video_path = build_video(
            args.audio_path,
            topic,
            topic,
            args.captions_path,
            template=args.template,
            image_paths=image_paths,
            video_format=args.video_format,
        )
        outputs = {
            "video": video_path,
            "template": args.template,
            "video_format": args.video_format,
            "images_used": bool(image_paths),
            "image_count": len(image_paths),
        }

        print("\nSaved video path:")
        print(video_path)

        log_success(topic, args.mode, outputs, args.organize)
        return

    script = generate_script(
        topic,
        target_duration_seconds=args.target_duration_seconds,
    )

    narration_text = ensure_call_to_action(clean_narration_text(script))

    script_path = save_script(topic, script)
    outputs = {"script": script_path}

    if args.mode in ["full", "script"]:
        print("\nGenerated Script:")
        print(script)

    print("\nSaved script path:")
    print(script_path)

    if args.mode == "script":
        log_success(topic, args.mode, outputs, args.organize)
        return

    if args.mode == "metadata":
        metadata_path = save_video_metadata(topic, script, topic)
        outputs["metadata"] = metadata_path

        print("\nSaved metadata path:")
        print(metadata_path)

        log_success(topic, args.mode, outputs, args.organize)
        return

    if args.mode == "captions":
        captions_path = save_srt_captions(
            narration_text,
            topic,
            words_per_caption=args.words_per_caption,
            seconds_per_caption=args.seconds_per_caption,
        )
        outputs["captions"] = captions_path
        outputs["words_per_caption"] = args.words_per_caption
        outputs["seconds_per_caption"] = args.seconds_per_caption

        print("\nSaved captions path:")
        print(captions_path)

        log_success(topic, args.mode, outputs, args.organize)
        return

    if args.mode == "full":
        metadata_path = save_video_metadata(topic, script, topic)
        outputs["metadata"] = metadata_path

        print("\nSaved metadata path:")
        print(metadata_path)

        if args.use_ai_images:
            image_paths = generate_scene_images(
                topic,
                narration_text,
                topic,
                image_count=args.image_count,
                template=args.template,
                video_format=args.video_format,
            )
            outputs["images"] = image_paths
            outputs["ai_images_used"] = True
            outputs["image_count"] = len(image_paths)

            print("\nSaved AI image paths:")
            for image_path in image_paths:
                print(image_path)

        if args.generate_thumbnail:
            thumbnail_source_paths = None

            if image_paths and not args.use_ai_thumbnail:
                thumbnail_source_paths = [image_paths[0]]

            thumbnail_path = generate_thumbnail(
                topic,
                topic,
                source_image_paths=thumbnail_source_paths,
                use_ai=args.use_ai_thumbnail,
                template=args.template,
            )
            outputs["thumbnail"] = thumbnail_path

            print("\nSaved thumbnail path:")
            print(thumbnail_path)

    audio_path = generate_voiceover(narration_text, topic)
    outputs["audio"] = audio_path

    print("\nSaved audio path:")
    print(audio_path)

    if args.mode == "voiceover":
        log_success(topic, args.mode, outputs, args.organize)
        return

    captions_path = None

    if args.mode == "full":
        audio_duration = get_audio_duration_seconds(audio_path)
        captions_path = save_srt_captions(
            narration_text,
            topic,
            words_per_caption=args.words_per_caption,
            seconds_per_caption=args.seconds_per_caption,
            total_duration_seconds=audio_duration,
            start_offset_seconds=args.caption_offset,
        )
        outputs["captions"] = captions_path
        outputs["caption_offset"] = args.caption_offset
        outputs["words_per_caption"] = args.words_per_caption
        outputs["seconds_per_caption"] = args.seconds_per_caption

        print("\nSaved captions path:")
        print(captions_path)

    video_path = build_video(
        audio_path,
        topic,
        topic,
        captions_path,
        template=args.template,
        image_paths=image_paths,
        video_format=args.video_format,
    )
    outputs["video"] = video_path
    outputs["template"] = args.template
    outputs["video_format"] = args.video_format
    outputs["images_used"] = bool(image_paths)
    outputs["image_count"] = len(image_paths)

    print("\nSaved video path:")
    print(video_path)

    log_success(topic, args.mode, outputs, args.organize)


if __name__ == "__main__":
    main()
