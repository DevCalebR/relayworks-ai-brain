import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

AUDIO_OUTPUT_DIR = Path("outputs/audio")

# Default ElevenLabs public/sample voice used when ELEVENLABS_VOICE_ID is unset.
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_TTS_MAX_CHARS = 9000

_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")


def _safe_filename(name):
    safe_name = name.lower()
    safe_name = re.sub(r"[^a-z0-9]+", "-", safe_name)
    safe_name = safe_name.strip("-")
    return safe_name or "voiceover"


def _append_text_chunk(chunks, current_chunk, text, separator, max_chars):
    candidate = f"{current_chunk}{separator}{text}" if current_chunk else text

    if len(candidate) <= max_chars:
        return candidate

    if current_chunk:
        chunks.append(current_chunk.strip())

    return text


def _split_sentence_on_words(sentence, max_chars):
    chunks = []
    current_chunk = ""

    for word in sentence.split():
        if len(word) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            for index in range(0, len(word), max_chars):
                chunks.append(word[index : index + max_chars])

            continue

        current_chunk = _append_text_chunk(
            chunks,
            current_chunk,
            word,
            " ",
            max_chars,
        )

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _split_paragraph_into_sentences(paragraph, max_chars):
    sentence_chunks = []

    for sentence in _SENTENCE_BOUNDARY_RE.split(paragraph):
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(sentence) <= max_chars:
            sentence_chunks.append(sentence)
            continue

        sentence_chunks.extend(_split_sentence_on_words(sentence, max_chars))

    return sentence_chunks


def split_text_for_tts(text, max_chars=DEFAULT_TTS_MAX_CHARS):
    """
    Split narration text into ElevenLabs-safe chunks.

    The splitter prefers paragraph boundaries, then sentence boundaries, then
    word boundaries for unusually long sentences.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    if not text or not text.strip():
        raise ValueError("Voiceover text is empty")

    normalized_text = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", normalized_text)
        if paragraph.strip()
    ]

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            current_chunk = _append_text_chunk(
                chunks,
                current_chunk,
                paragraph,
                "\n\n",
                max_chars,
            )
            continue

        first_sentence = True

        for sentence_chunk in _split_paragraph_into_sentences(paragraph, max_chars):
            separator = "\n\n" if first_sentence else " "
            current_chunk = _append_text_chunk(
                chunks,
                current_chunk,
                sentence_chunk,
                separator,
                max_chars,
            )
            first_sentence = False

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [chunk for chunk in chunks if chunk.strip()]


def _post_elevenlabs_voiceover(url, headers, text):
    payload = {
        "text": text,
        "model_id": DEFAULT_MODEL_ID,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.25,
            "use_speaker_boost": True,
        },
    }

    return requests.post(url, headers=headers, json=payload, timeout=120)


def _combine_audio_parts(part_paths, output_path):
    try:
        from moviepy import AudioFileClip, concatenate_audioclips
    except ImportError as exc:
        raise RuntimeError(
            "MoviePy is required to combine ElevenLabs audio chunks"
        ) from exc

    clips = []
    combined_clip = None

    try:
        clips = [AudioFileClip(str(part_path)) for part_path in part_paths]
        combined_clip = concatenate_audioclips(clips)
        combined_clip.write_audiofile(str(output_path), codec="libmp3lame")
    except Exception as exc:
        raise RuntimeError(
            "Failed to combine ElevenLabs audio chunks into "
            f"{output_path}: {exc}"
        ) from exc
    finally:
        if combined_clip is not None:
            combined_clip.close()

        for clip in clips:
            clip.close()


def generate_voiceover(text, output_name):
    """
    Generate an ElevenLabs voiceover MP3 from text.

    Args:
        text: The script text to convert into speech.
        output_name: A human-readable name used to create the output filename.

    Returns:
        The saved MP3 file path as a string.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set")

    if not text or not text.strip():
        raise ValueError("Voiceover text is empty")

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)

    AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    slug = _safe_filename(output_name)
    filename = f"{slug}.mp3"
    output_path = AUDIO_OUTPUT_DIR / filename

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        f"?output_format={DEFAULT_OUTPUT_FORMAT}"
    )

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    if len(text) <= DEFAULT_TTS_MAX_CHARS:
        response = _post_elevenlabs_voiceover(url, headers, text)

        if response.status_code != 200:
            raise RuntimeError(
                "ElevenLabs voiceover generation failed: "
                f"{response.status_code} {response.text}"
            )

        output_path.write_bytes(response.content)

        return str(output_path)

    chunks = split_text_for_tts(text, max_chars=DEFAULT_TTS_MAX_CHARS)
    total_chunks = len(chunks)
    part_number_padding = max(2, len(str(total_chunks)))
    part_paths = []

    for chunk_number, chunk_text in enumerate(chunks, start=1):
        part_filename = f"{slug}-part-{chunk_number:0{part_number_padding}d}.mp3"
        part_path = AUDIO_OUTPUT_DIR / part_filename
        response = _post_elevenlabs_voiceover(url, headers, chunk_text)

        if response.status_code != 200:
            raise RuntimeError(
                "ElevenLabs voiceover generation failed for "
                f"chunk {chunk_number}/{total_chunks}: "
                f"{response.status_code} {response.text}"
            )

        part_path.write_bytes(response.content)
        part_paths.append(part_path)

    _combine_audio_parts(part_paths, output_path)

    return str(output_path)
