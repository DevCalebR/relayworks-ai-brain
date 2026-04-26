from agents.script_agent import generate_script
from tools.file_writer import save_script
from tools.voiceover import generate_voiceover


def main():
    topic = "How people are making money with AI in 2026"

    script = generate_script(topic)

    print("\nGenerated Script:")
    print(script)

    script_path = save_script(topic, script)

    print("\nSaved script path:")
    print(script_path)

    audio_path = generate_voiceover(script, topic)

    print("\nSaved audio path:")
    print(audio_path)


if __name__ == "__main__":
    main()
