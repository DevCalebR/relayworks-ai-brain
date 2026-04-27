import argparse

from agents.script_agent import generate_script
from tools.file_writer import save_script
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
        choices=["full", "script", "voiceover", "video", "test-audio"],
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


def main():
    args = parse_args()
    topic = args.topic

    if args.mode == "test-audio":
        audio_path = create_test_audio(topic)

        print("\nSaved audio path:")
        print(audio_path)
        return

    if args.mode == "video":
        if not args.audio_path:
            raise ValueError("--audio-path is required when --mode video")

        video_path = build_video(args.audio_path, topic, topic)

        print("\nSaved video path:")
        print(video_path)
        return

    script = generate_script(topic)

    script_path = save_script(topic, script)

    if args.mode in ["full", "script"]:
        print("\nGenerated Script:")
        print(script)

    print("\nSaved script path:")
    print(script_path)

    if args.mode == "script":
        return

    audio_path = generate_voiceover(script, topic)

    print("\nSaved audio path:")
    print(audio_path)

    if args.mode == "voiceover":
        return

    video_path = build_video(audio_path, topic, topic)

    print("\nSaved video path:")
    print(video_path)


if __name__ == "__main__":
    main()
