import argparse
import json

from moviepy import AudioFileClip

from agents.script_agent import generate_script
from tools.captions import save_srt_captions
from tools.file_writer import save_script
from tools.image_generator import generate_scene_images
from tools.image_inputs import collect_image_paths
from tools.logger import log_pipeline_run
from tools.metadata import save_video_metadata
from tools.run_folder import organize_run_outputs
from tools.test_audio import create_test_audio
from tools.text_cleaner import clean_narration_text, ensure_call_to_action
from tools.thumbnail_generator import generate_thumbnail
from tools.upload_check import validate_upload_package
from tools.voiceover import generate_voiceover
from tools.video_builder import build_video
from tools.youtube_api import upload_video_from_run_folder


DEFAULT_TOPIC = "How people are making money with AI in 2026"


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
        ],
        default="full",
        help="Pipeline mode to run.",
    )
    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help="Topic to use for script generation or video title.",
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
        "--organize",
        action="store_true",
        help="Copy generated outputs into a timestamped local run folder.",
    )
    parser.add_argument(
        "--caption-offset",
        type=float,
        default=0.5,
        help="Caption start offset in seconds used when full mode has audio duration.",
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


def main():
    args = parse_args()
    topic = args.topic
    image_paths = []

    if args.image_count <= 0:
        raise ValueError("--image-count must be greater than 0")

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
        )
        outputs = {
            "video": video_path,
            "template": args.template,
            "images_used": bool(image_paths),
            "image_count": len(image_paths),
        }

        print("\nSaved video path:")
        print(video_path)

        log_success(topic, args.mode, outputs, args.organize)
        return

    script = generate_script(topic)

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
        captions_path = save_srt_captions(narration_text, topic)
        outputs["captions"] = captions_path

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
            total_duration_seconds=audio_duration,
            start_offset_seconds=args.caption_offset,
        )
        outputs["captions"] = captions_path
        outputs["caption_offset"] = args.caption_offset

        print("\nSaved captions path:")
        print(captions_path)

    video_path = build_video(
        audio_path,
        topic,
        topic,
        captions_path,
        template=args.template,
        image_paths=image_paths,
    )
    outputs["video"] = video_path
    outputs["template"] = args.template
    outputs["images_used"] = bool(image_paths)
    outputs["image_count"] = len(image_paths)

    print("\nSaved video path:")
    print(video_path)

    log_success(topic, args.mode, outputs, args.organize)


if __name__ == "__main__":
    main()
