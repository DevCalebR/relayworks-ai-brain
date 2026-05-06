import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


DEFAULT_TARGET_DURATION_SECONDS = 150
DEFAULT_SHORT_TARGET_DURATION_SECONDS = 45


def _estimate_word_range(target_duration_seconds: int) -> tuple[int, int]:
    target_words = target_duration_seconds * 2.6
    min_words = max(80, round(target_words * 0.82))
    max_words = max(min_words + 40, round(target_words * 1.15))
    return min_words, max_words


def _estimate_short_word_range(target_duration_seconds: int) -> tuple[int, int]:
    target_words = target_duration_seconds * 2.55
    min_words = max(60, round(target_words * 0.78))
    max_words = max(min_words + 20, round(target_words * 1.12))

    if 35 <= target_duration_seconds <= 60:
        min_words = max(min_words, 80)
        max_words = min(max_words, 130)

    return min_words, max_words


def generate_script(
    topic: str,
    target_duration_seconds: int = DEFAULT_TARGET_DURATION_SECONDS,
) -> str:
    if target_duration_seconds <= 0:
        raise ValueError("target_duration_seconds must be greater than 0")

    min_words, max_words = _estimate_word_range(target_duration_seconds)

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write highly engaging short episode-style YouTube narration for "
                    "weird history, mysteries, scary factual stories, strange historical "
                    "events, dark history, and eerie true stories. The default format is "
                    "a concise 2-3 minute mystery/documentary episode, not an ultra-short "
                    "Shorts script. Keep the tone factual, suspenseful, cinematic, and "
                    "curiosity-driven without inventing claims or using gore for shock."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Write a highly engaging short episode-style YouTube narration about: {topic}\n\n"
                    "Requirements:\n"
                    f"- Target about {target_duration_seconds} seconds of spoken narration.\n"
                    f"- Aim for roughly {min_words}-{max_words} words, with concise but complete storytelling.\n"
                    "- Start with a 1-2 sentence hook that creates immediate curiosity.\n"
                    "- Set up who, what, where, and when without slowing the pace.\n"
                    "- Escalate with strange details, contradictions, discoveries, or eerie facts.\n"
                    "- Build a strong middle that keeps revealing information and suspense.\n"
                    "- End with either a strong partial conclusion, the strongest theory, or an honest unresolved question.\n"
                    "- Make the final line before the call to action create curiosity or leave a lingering thought.\n"
                    "- Make it feel like part of a mystery or documentary series episode.\n"
                    "- Allow a mild what-happens-next feeling when appropriate, but do not force a fake cliffhanger.\n"
                    "- Stay factual-sounding and narrate uncertainty honestly when it exists.\n"
                    "- Avoid fake claims presented as fact.\n"
                    "- Avoid gore for shock value.\n"
                    "- Avoid fictional horror framing unless the topic is clearly a legend or myth.\n"
                    "- Optimize for high viewer retention.\n"
                    "- Use simple language.\n"
                    "- End with exactly one short, natural call to action that fits weird history, mysteries, and eerie factual stories.\n"
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


def generate_short_script(
    topic: str,
    target_duration_seconds: int = DEFAULT_SHORT_TARGET_DURATION_SECONDS,
    niche: str = "weird history and strange true stories",
    audience: str = "fans of weird history, mysteries, and eerie true stories",
) -> str:
    if target_duration_seconds <= 0:
        raise ValueError("target_duration_seconds must be greater than 0")

    min_words, max_words = _estimate_short_word_range(target_duration_seconds)

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write factual YouTube Shorts narration for weird history, "
                    "mysteries, scary factual stories, dark history, strange historical "
                    "events, and eerie true stories. Keep every Short fast, focused, "
                    "hook-driven, and honest about uncertainty. Do not invent claims "
                    "or frame fiction as fact."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Write one YouTube Shorts narration about: {topic}\n\n"
                    f"Niche: {niche}\n"
                    f"Audience: {audience}\n"
                    f"Target spoken duration: about {target_duration_seconds} seconds\n"
                    f"Target word range: roughly {min_words}-{max_words} words\n\n"
                    "Requirements:\n"
                    "- Make this a standalone Short, not an episode or series chapter.\n"
                    "- Spoken narration only.\n"
                    "- Start with a strong hook in the first sentence.\n"
                    "- Keep the story focused on one core idea only.\n"
                    "- Move quickly: hook, setup, strangest detail, honest context, ending thought.\n"
                    "- Keep the tone factual edutainment, not fictional horror.\n"
                    "- Phrase uncertainty honestly when historians disagree or records are unclear.\n"
                    "- Avoid fake claims presented as fact.\n"
                    "- Avoid gore for shock value.\n"
                    "- End with exactly one short, natural call to action.\n"
                    "- Do not mention AI business, side hustles, or making money in the call to action.\n"
                    "- Do not include markdown.\n"
                    "- Do not include speaker labels.\n"
                    "- Do not include timestamps.\n"
                    "- Do not include scene directions.\n"
                    "- Do not include camera directions.\n"
                    "- Do not include bullets or numbered lists.\n"
                    "- Output only the words that should be spoken aloud."
                ),
            },
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""


def generate_episode_script_from_chapter(
    episode_source,
    target_duration_seconds: int = DEFAULT_TARGET_DURATION_SECONDS,
) -> str:
    if target_duration_seconds <= 0:
        raise ValueError("target_duration_seconds must be greater than 0")

    min_words, max_words = _estimate_word_range(target_duration_seconds)
    episode_plan = episode_source["episode_plan"]
    series_bible = episode_source["series_bible"]
    previous_episode = episode_source.get("previous_episode")
    next_episode = episode_source.get("next_episode")

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write narration-only YouTube episode scripts for factual "
                    "weird history, mysteries, dark history, strange historical events, "
                    "and eerie true stories. Keep the tone eerie, cinematic, mysterious, "
                    "factual, and compelling. Never invent facts beyond the supplied "
                    "series bible, chapter context, and episode plan."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write the next episode script from this series source material.\n\n"
                    f"Target spoken duration: {target_duration_seconds} seconds\n"
                    f"Target word range: roughly {min_words}-{max_words} words\n\n"
                    f"Series bible:\n{json.dumps(series_bible, indent=2)}\n\n"
                    f"Episode plan:\n{json.dumps(episode_plan, indent=2)}\n\n"
                    f"Previous episode:\n{json.dumps(previous_episode, indent=2)}\n\n"
                    f"Next episode:\n{json.dumps(next_episode, indent=2)}\n\n"
                    f"Chapter source material:\n{episode_source['chapter_text']}\n\n"
                    "Requirements:\n"
                    "- Produce narration-only output.\n"
                    "- No markdown.\n"
                    "- No bullets.\n"
                    "- No speaker labels.\n"
                    "- No timestamps.\n"
                    "- No scene directions.\n"
                    "- No camera directions.\n"
                    "- No bracketed production notes.\n"
                    "- Keep the episode aligned with the target duration.\n"
                    "- Make it feel like part of a series.\n"
                    "- Avoid repeating previous episode content too much.\n"
                    "- Use continuity_from_previous to begin naturally.\n"
                    "- Use ending_tease and next_episode_setup to end naturally.\n"
                    "- End with exactly one short natural call to action.\n"
                    "- Do not invent facts beyond the series bible and chapter context.\n"
                    "- Present uncertainty honestly.\n"
                    "- Avoid graphic gore.\n"
                    "- Output only words that should be spoken aloud."
                ),
            },
        ],
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""
