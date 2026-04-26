from agents.script_agent import generate_script
from tools.file_writer import save_script


def main() -> None:
    topic = "How people are making money with AI in 2026"
    script = generate_script(topic)
    print(script)
    saved_path = save_script(topic, script)
    print(saved_path)


if __name__ == "__main__":
    main()
