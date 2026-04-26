import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def generate_script(topic: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write highly engaging YouTube scripts designed for short-form "
                    "viewer retention and clear delivery."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Write a highly engaging 60-90 second YouTube script about: {topic}\n\n"
                    "Requirements:\n"
                    "- Hook the viewer in the first 3 seconds.\n"
                    "- Optimize for high viewer retention.\n"
                    "- Use simple language.\n"
                    "- Keep the script 60-90 seconds long.\n"
                    "- Return only the script text."
                ),
            },
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""
