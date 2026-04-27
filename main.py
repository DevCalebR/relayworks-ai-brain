import argparse

from agents.script_agent import generate_script
from tools.captions import save_srt_captions
from tools.file_writer import save_script
from tools.logger import log_pipeline_run
from tools.test_audio import create_test_audio
from tools.voiceover import generate_voiceover
from tools.video_builder import build_video


DEFAULT_TOPIC = "How people are making money with AI in 2026"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run specific parts of the RelayWorks AI Content Brain pipeline."
    )
    parser.add_argument(
        "--mode",
        choices=["full", "script", "voiceover", "video", "test-audio", "captions"],
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
    return parser.parse_args()


def log_success(topic, mode, outputs):
    log_entry = log_pipeline_run(topic, mode, outputs)

    print("\nLogged pipeline run:")
    print(log_entry)


def main():
    args = parse_args()
    topic = args.topic

    if args.mode == "test-audio":
        audio_path = create_test_audio(topic)
        outputs = {"audio": audio_path}

        print("\nSaved audio path:")
        print(audio_path)

        log_success(topic, args.mode, outputs)
        return

    if args.mode == "video":
        if not args.audio_path:
            raise ValueError("--audio-path is required when --mode video")

        video_path = build_video(args.audio_path, topic, topic)
        outputs = {"video": video_path}

        print("\nSaved video path:")
        print(video_path)

        log_success(topic, args.mode, outputs)
        return

    script = generate_script(topic)

    script_path = save_script(topic, script)
    outputs = {"script": script_path}

    if args.mode in ["full", "script"]:
        print("\nGenerated Script:")
        print(script)

    print("\nSaved script path:")
    print(script_path)

    if args.mode == "script":
        log_success(topic, args.mode, outputs)
        return

    if args.mode in ["full", "captions"]:
        captions_path = save_srt_captions(script, topic)
        outputs["captions"] = captions_path

        print("\nSaved captions path:")
        print(captions_path)

    if args.mode == "captions":
        log_success(topic, args.mode, outputs)
        return

    audio_path = generate_voiceover(script, topic)
    outputs["audio"] = audio_path

    print("\nSaved audio path:")
    print(audio_path)

    if args.mode == "voiceover":
        log_success(topic, args.mode, outputs)
        return

    video_path = build_video(audio_path, topic, topic)
    outputs["video"] = video_path

    print("\nSaved video path:")
    print(video_path)

    log_success(topic, args.mode, outputs)


if __name__ == "__main__":
    main()
