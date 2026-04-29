import re


_SPEAKER_LABEL_PATTERN = re.compile(
    r"(?im)^\s*(?:[*_~`]+\s*)?"
    r"(?:-\s*)?"
    r"(?:narrator|host|voiceover|vo|on[-\s]?screen\s+text)"
    r"\s*:\s*(?:[*_~`]+\s*)?"
)

_TIMESTAMP_DIRECTION_PATTERN = re.compile(
    r"[\[(]\s*(?:\d{1,2}:)?\d{1,2}:\d{2}\s*-\s*(?:\d{1,2}:)?\d{1,2}:\d{2}\s*[\])]"
)

_BRACKETED_DIRECTION_PATTERN = re.compile(r"[\[(]\s*[A-Z][A-Z0-9\s\-_:]{1,60}\s*[\])]")

_COMMON_DIRECTION_PATTERN = re.compile(
    r"[\[(]\s*"
    r"(?:intro|outro|cut\s+to|on\s+screen\s+text|scene|b-roll|camera|music|sfx|"
    r"beat|pause|title|text|visual|show|close-up|wide\s+shot)"
    r"[^\]\)]{0,60}\s*[\])]",
    flags=re.IGNORECASE,
)

_MARKDOWN_MARKER_PATTERN = re.compile(r"[*_`#>]+")

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE,
)

_CTA_PATTERN = re.compile(
    r"\b(?:subscribe|like\s+this\s+video|follow|comment\s+below)\b",
    flags=re.IGNORECASE,
)

_DEFAULT_CTA = (
    "If this helped, like this video and subscribe for more AI business ideas."
)


def _collapse_whitespace(text):
    collapsed_text = re.sub(r"[ \t]+", " ", text)
    collapsed_text = re.sub(r"\s*\n\s*", " ", collapsed_text)
    collapsed_text = re.sub(r"\s{2,}", " ", collapsed_text)
    return collapsed_text.strip()


def clean_narration_text(text):
    """
    Return narration-only text suitable for text-to-speech and captions.
    """
    cleaned_text = str(text or "")
    cleaned_text = _TIMESTAMP_DIRECTION_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _COMMON_DIRECTION_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _BRACKETED_DIRECTION_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _SPEAKER_LABEL_PATTERN.sub("", cleaned_text)
    cleaned_text = _MARKDOWN_MARKER_PATTERN.sub("", cleaned_text)
    cleaned_text = _EMOJI_PATTERN.sub("", cleaned_text)
    return _collapse_whitespace(cleaned_text)


def ensure_call_to_action(text):
    """
    Ensure narration ends with a short natural call to action.
    """
    narration_text = _collapse_whitespace(str(text or ""))

    if not narration_text:
        return _DEFAULT_CTA

    if _CTA_PATTERN.search(narration_text):
        return narration_text

    return _collapse_whitespace(f"{narration_text} {_DEFAULT_CTA}")
