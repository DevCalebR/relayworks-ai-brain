import re
from pathlib import Path

from tools.text_cleaner import clean_narration_text


CAPTIONS_OUTPUT_DIR = Path("outputs/captions")


def _safe_filename(name):
    safe_name = str(name).lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "captions"


def _format_srt_timestamp(seconds):
    total_milliseconds = int(round(seconds * 1000))
    milliseconds = total_milliseconds % 1000
    total_seconds = total_milliseconds // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def _chunk_words(words, chunk_size):
    for start_index in range(0, len(words), chunk_size):
        yield words[start_index : start_index + chunk_size]


def save_srt_captions(
    script,
    output_name,
    words_per_caption=8,
    seconds_per_caption=2.5,
    total_duration_seconds=None,
):
    """
    Save simple SRT captions from script text using fixed word chunks.

    Args:
        script: Script text to split into captions.
        output_name: Human-readable name used to create the output filename.
        words_per_caption: Number of words per caption.
        seconds_per_caption: Duration assigned to each caption.
        total_duration_seconds: Optional total duration used to align captions.

    Returns:
        The saved SRT file path as a string.
    """
    if words_per_caption <= 0:
        raise ValueError("words_per_caption must be greater than 0")

    if seconds_per_caption <= 0:
        raise ValueError("seconds_per_caption must be greater than 0")

    if total_duration_seconds is not None and total_duration_seconds <= 0:
        raise ValueError("total_duration_seconds must be greater than 0")

    words = clean_narration_text(script).split()

    if not words:
        raise ValueError("Caption script is empty")

    CAPTIONS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = CAPTIONS_OUTPUT_DIR / f"{_safe_filename(output_name)}.srt"

    caption_blocks = []

    word_chunks = list(_chunk_words(words, words_per_caption))
    caption_count = len(word_chunks)

    for index, caption_words in enumerate(word_chunks, start=1):
        if total_duration_seconds is None:
            start_time = (index - 1) * seconds_per_caption
            end_time = index * seconds_per_caption
        else:
            start_time = (index - 1) * total_duration_seconds / caption_count
            end_time = index * total_duration_seconds / caption_count

        caption_text = " ".join(caption_words)

        caption_blocks.append(
            "\n".join(
                [
                    str(index),
                    (
                        f"{_format_srt_timestamp(start_time)} --> "
                        f"{_format_srt_timestamp(end_time)}"
                    ),
                    caption_text,
                ]
            )
        )

    output_path.write_text("\n\n".join(caption_blocks) + "\n", encoding="utf-8")

    return str(output_path)
