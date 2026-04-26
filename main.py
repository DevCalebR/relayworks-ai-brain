from agents.script_agent import generate_script


def main() -> None:
    topic = "How people are making money with AI in 2026"
    script = generate_script(topic)
    print(script)


if __name__ == "__main__":
    main()
