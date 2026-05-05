import argparse
import json
from datetime import datetime
from pathlib import Path

from moviepy import AudioFileClip

from agents.script_agent import generate_episode_script_from_chapter, generate_script
from tools.captions import save_srt_captions
from tools.file_writer import save_script
from tools.image_generator import generate_scene_images
from tools.image_inputs import collect_image_paths
from tools.logger import log_pipeline_run
from tools.metadata import save_video_metadata
from tools.run_folder import organize_run_outputs
from tools.series_planner import (
    create_series_plan,
    get_episode_source,
    load_series_plan,
    save_series_plan,
)
from tools.test_audio import create_test_audio
from tools.text_cleaner import clean_narration_text, ensure_call_to_action
from tools.thumbnail_generator import generate_thumbnail
from tools.topic_research import research_topics, save_topic_research
from tools.upload_check import validate_upload_package
from tools.voiceover import generate_voiceover
from tools.video_builder import build_video
from tools.youtube_api import upload_video_from_run_folder


DEFAULT_TOPIC = "The strangest disappearance in history"
DEFAULT_TARGET_DURATION_SECONDS = 150
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
            "batch-series",
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
        help="Niche to research when --mode topic-research.",
    )
    parser.add_argument(
        "--audience",
        help="Optional audience to target when --mode topic-research.",
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
        default=5,
        help="Number of episodes to plan when --mode series-plan.",
    )
    parser.add_argument(
        "--series-folder",
        help="Series folder path required when --mode batch-series.",
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


def get_audio_duration_seconds(audio_path):
    audio_clip = AudioFileClip(audio_path)

    try:
        return audio_clip.duration
    finally:
        audio_clip.close()


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


def _write_batch_summary(summary):
    BATCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    series_slug = Path(summary["series_folder"]).name or "series"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary_path = BATCH_OUTPUT_DIR / f"{series_slug}-batch-{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return str(summary_path)


def _write_episode_record(series_folder, episode_source, result):
    episode_plan = episode_source["episode_plan"]
    episode_number = int(episode_plan["episode_number"])
    episodes_folder = Path(series_folder) / "episodes"
    episodes_folder.mkdir(parents=True, exist_ok=True)

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
        "youtube_video_id": None,
    }

    record_path = episodes_folder / f"episode-{episode_number:02d}.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return str(record_path)


def generate_full_outputs(topic, script, args):
    narration_text = ensure_call_to_action(clean_narration_text(script))
    script_path = save_script(topic, script)
    outputs = {"script": script_path}

    metadata_path = save_video_metadata(topic, script, topic)
    outputs["metadata"] = metadata_path

    print("\nSaved metadata path:")
    print(metadata_path)

    image_paths = []
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

    return outputs


def run_batch_series(args):
    if not args.series_folder:
        raise ValueError("--series-folder is required when --mode batch-series")

    loaded_plan = load_series_plan(args.series_folder)
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

            outputs = generate_full_outputs(topic, script, args)
            run_folder = None
            upload_check_result = None

            if args.organize:
                organize_result = organize_run_outputs(topic, outputs)
                run_folder = organize_result["run_folder"]
                outputs["run_folder"] = run_folder
                outputs["copied_outputs"] = organize_result["copied_outputs"]

                print("\nOrganized run folder:")
                print(run_folder)

                upload_check_result = validate_upload_package(run_folder)
                outputs["upload_check_result"] = upload_check_result

                print("\nUpload check result:")
                print(json.dumps(upload_check_result, indent=2))

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

    if args.episodes <= 0:
        raise ValueError("--episodes must be greater than 0")

    if args.mode == "series-plan":
        if not args.topic:
            raise ValueError("--topic is required when --mode series-plan")

        series_plan = create_series_plan(
            topic=args.topic,
            episodes=args.episodes,
            target_duration_seconds=args.target_duration_seconds,
            audience=args.audience,
        )
        saved_paths = save_series_plan(series_plan)
        print_series_plan_result(saved_paths)
        return

    if args.mode == "batch-series":
        run_batch_series(args)
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
