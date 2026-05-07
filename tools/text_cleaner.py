import re


_SPEAKER_LABEL_PATTERN = re.compile(
    r"(?im)^\s*(?:[*_~`]+\s*)?"
    r"(?:-\s*)?"
    r"(?:narrator|host|voiceover|vo|on[-\s]?screen\s+text)"
    r"\s*:\s*(?:[*_~`]+\s*)?"
)

_TOPIC_LABEL_PATTERN = re.compile(r"(?im)^\s*topic:\s*.*(?:\n|$)")

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

_SENTENCE_PATTERN = re.compile(r"[^.!?]+(?:[.!?]+|$)")

_LIKE_CTA_PATTERN = re.compile(
    r"\b(?:"
    r"like\s+this\s+video|"
    r"like\s+the\s+video|"
    r"like\s*(?:,|and|&)\s*subscribe|"
    r"hit\s+(?:the\s+)?like|"
    r"leave\s+a\s+like|"
    r"please\s+like|"
    r"to\s+like"
    r")\b",
    flags=re.IGNORECASE,
)

_SUBSCRIBE_CTA_PATTERN = re.compile(
    r"\b(?:subscribe|hit\s+(?:the\s+)?subscribe)\b",
    flags=re.IGNORECASE,
)

_OTHER_CTA_PATTERN = re.compile(
    r"\b(?:"
    r"follow(?:\s+for\s+more)?|"
    r"comment\s+below|"
    r"dive\s+into\s+the\s+comments|"
    r"share\s+your\s+thoughts|"
    r"for\s+more\s+(?:stories|mysteries|strange\s+history)|"
    r"if\s+you\s+want\s+more|"
    r"if\s+this\s+helped|"
    r"want\s+more\s+stories"
    r")\b",
    flags=re.IGNORECASE,
)

_OFF_NICHE_CTA_PATTERN = re.compile(
    r"\b(?:ai\s+business|business\s+ideas|side\s+hustles|making\s+money)\b",
    flags=re.IGNORECASE,
)

_CTA_START_PATTERN = re.compile(
    r"(?:^|[,:;.!?]\s+|\b(?:so|and|then)\s+)"
    r"(?="
    r"(?:if\s+(?:you\s+want\s+more|this\s+helped)|"
    r"want\s+more\s+stories|"
    r"(?:please\s+)?(?:like|subscribe)\b|"
    r"hit\s+(?:the\s+)?(?:like|subscribe)|"
    r"leave\s+a\s+like|"
    r"(?:do\s+not|don't)\s+forget\s+to\s+(?:like|subscribe)|"
    r"remember\s+to\s+(?:like|subscribe)|"
    r"follow\b|"
    r"comment\b|"
    r"dive\s+into\s+the\s+comments|"
    r"share\b)"
    r")",
    flags=re.IGNORECASE,
)

_DEFAULT_CTA = (
    "If you want more strange stories like this, like this video and subscribe."
)


def _collapse_whitespace(text):
    collapsed_text = re.sub(r"[ \t]+", " ", text)
    collapsed_text = re.sub(r"\s*\n\s*", " ", collapsed_text)
    collapsed_text = re.sub(r"\s{2,}", " ", collapsed_text)
    return collapsed_text.strip()


def _split_sentences(text):
    return [
        match.group(0).strip()
        for match in _SENTENCE_PATTERN.finditer(text)
        if match.group(0).strip()
    ]


def _has_like_cta(text):
    if _LIKE_CTA_PATTERN.search(text):
        return True

    return bool(re.search(r"^\s*(?:please\s+)?like\b", text, flags=re.IGNORECASE))


def _has_subscribe_cta(text):
    return bool(_SUBSCRIBE_CTA_PATTERN.search(text))


def _is_complete_cta(text):
    return (
        _has_like_cta(text)
        and _has_subscribe_cta(text)
        and not _OFF_NICHE_CTA_PATTERN.search(text)
    )


def _is_cta_sentence(text):
    return (
        _has_like_cta(text)
        or _has_subscribe_cta(text)
        or bool(_OTHER_CTA_PATTERN.search(text))
    )


def _ensure_terminal_punctuation(text):
    if not text:
        return text

    if text[-1] in ".!?":
        return text

    return f"{text}."


def _remove_cta_from_sentence(sentence):
    if not _is_cta_sentence(sentence):
        return sentence

    cta_match = _CTA_START_PATTERN.search(sentence)
    if not cta_match:
        return ""

    remaining_sentence = sentence[: cta_match.start()].strip(" ,;:-")
    if not remaining_sentence or _is_cta_sentence(remaining_sentence):
        return ""

    return _ensure_terminal_punctuation(remaining_sentence)


def _remove_cta_sentences(sentences, keep_final_cta=False):
    final_index = len(sentences) - 1
    cleaned_sentences = []

    for index, sentence in enumerate(sentences):
        if keep_final_cta and index == final_index:
            cleaned_sentences.append(sentence)
            continue

        cleaned_sentence = _remove_cta_from_sentence(sentence)
        if cleaned_sentence:
            cleaned_sentences.append(cleaned_sentence)

    return cleaned_sentences


def clean_narration_text(text):
    """
    Return narration-only text suitable for text-to-speech and captions.
    """
    cleaned_text = str(text or "")
    cleaned_text = _TOPIC_LABEL_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _TIMESTAMP_DIRECTION_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _COMMON_DIRECTION_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _BRACKETED_DIRECTION_PATTERN.sub(" ", cleaned_text)
    cleaned_text = _SPEAKER_LABEL_PATTERN.sub("", cleaned_text)
    cleaned_text = _MARKDOWN_MARKER_PATTERN.sub("", cleaned_text)
    cleaned_text = _EMOJI_PATTERN.sub("", cleaned_text)
    return _collapse_whitespace(cleaned_text)


def ensure_call_to_action(text):
    """
    Ensure narration ends with exactly one complete like-and-subscribe CTA.
    """
    narration_text = _collapse_whitespace(str(text or ""))

    if not narration_text:
        return _DEFAULT_CTA

    sentences = _split_sentences(narration_text)
    if not sentences:
        return _DEFAULT_CTA

    final_sentence = sentences[-1]
    if _is_complete_cta(final_sentence):
        cleaned_sentences = _remove_cta_sentences(sentences, keep_final_cta=True)
        return _collapse_whitespace(" ".join(cleaned_sentences))

    cleaned_sentences = _remove_cta_sentences(sentences)
    cleaned_narration = _collapse_whitespace(" ".join(cleaned_sentences))
    if not cleaned_narration:
        return _DEFAULT_CTA

    return _collapse_whitespace(f"{cleaned_narration} {_DEFAULT_CTA}")
