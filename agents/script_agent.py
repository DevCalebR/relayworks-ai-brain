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
                    "You write highly engaging YouTube Shorts scripts for weird history, "
                    "mysteries, scary factual stories, strange historical events, dark "
                    "history, and eerie true stories. Keep the tone factual, suspenseful, "
                    "and curiosity-driven without inventing claims or using gore for shock."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Write a highly engaging 60-90 second YouTube script about: {topic}\n\n"
                    "Requirements:\n"
                    "- Start with a strong curiosity hook in the first sentence.\n"
                    "- Build suspense quickly while staying factual-sounding.\n"
                    "- Avoid fake claims presented as fact.\n"
                    "- Avoid gore for shock value.\n"
                    "- Avoid fictional horror framing unless the topic is clearly a legend or myth.\n"
                    "- Optimize for high viewer retention.\n"
                    "- Use simple language.\n"
                    "- Keep the script 60-90 seconds long.\n"
                    "- End with exactly one short, natural call to action that fits "
                    "weird history, mysteries, and eerie factual stories.\n"
                    "- Do not mention AI business, side hustles, or making money in the call to action.\n"
                    "- Make the call to action sound natural, not overly salesy.\n"
                    "- Do not include speaker labels.\n"
                    "- Do not include markdown.\n"
                    "- Do not include timestamps.\n"
                    "- Do not include bracketed scene directions.\n"
                    "- Do not include camera directions.\n"
                    "- Output only the words that should be spoken aloud."
                ),
            },
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""
