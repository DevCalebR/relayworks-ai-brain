import json

from moviepy import AudioFileClip

from tools.captions import save_srt_captions
from tools.file_writer import save_script
from tools.image_generator import generate_scene_images
from tools.metadata import save_video_metadata
from tools.run_folder import copy_outputs_to_run_folder, organize_run_outputs
from tools.text_cleaner import clean_narration_text, ensure_call_to_action
from tools.thumbnail_generator import generate_thumbnail
from tools.upload_check import validate_upload_package
from tools.video_builder import build_video
from tools.voiceover import generate_voiceover


def get_audio_duration_seconds(audio_path):
    audio_clip = AudioFileClip(audio_path)

    try:
        return audio_clip.duration
    finally:
        audio_clip.close()


def generate_full_outputs(topic, script, args):
    narration_text = ensure_call_to_action(clean_narration_text(script))
    metadata_style = getattr(args, "metadata_style", "episode")
    script_path = save_script(topic, narration_text)
    outputs = {"script": script_path}

    metadata_path = save_video_metadata(
        topic,
        narration_text,
        topic,
        content_style=metadata_style,
    )
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


def run_full_generation_pipeline(topic, script, args):
    outputs = generate_full_outputs(topic, script, args)
    run_folder = None
    upload_check_result = None

    if args.organize:
        requested_run_folder = getattr(args, "run_folder", None)

        if requested_run_folder:
            copied_outputs = copy_outputs_to_run_folder(outputs, requested_run_folder)
            organize_result = {
                "run_folder": str(requested_run_folder),
                "copied_outputs": copied_outputs,
            }
        else:
            organize_result = organize_run_outputs(topic, outputs)

        run_folder = organize_result["run_folder"]
        outputs["run_folder"] = run_folder
        outputs["copied_outputs"] = organize_result["copied_outputs"]

        print("\nOrganized run folder:")
        print(run_folder)

        if getattr(args, "upload_ready_check", True):
            upload_check_result = validate_upload_package(run_folder)
            outputs["upload_check_result"] = upload_check_result

            print("\nUpload check result:")
            print(json.dumps(upload_check_result, indent=2))

    return outputs
