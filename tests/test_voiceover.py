import pytest

from tools.voiceover import split_text_for_tts


def test_split_text_for_tts_short_text_returns_one_chunk():
    text = "This is a short narration script."

    assert split_text_for_tts(text, max_chars=9000) == [text]


def test_split_text_for_tts_long_paragraph_splits_below_max_chars():
    text = " ".join(["narration"] * 80)
    chunks = split_text_for_tts(text, max_chars=120)

    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
    assert " ".join(chunks) == text


def test_split_text_for_tts_prefers_sentence_boundaries():
    text = (
        "First sentence ends here. "
        "Second sentence also ends here. "
        "Third sentence follows."
    )

    chunks = split_text_for_tts(text, max_chars=35)

    assert chunks == [
        "First sentence ends here.",
        "Second sentence also ends here.",
        "Third sentence follows.",
    ]


def test_split_text_for_tts_splits_long_sentence_on_word_boundaries():
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    chunks = split_text_for_tts(text, max_chars=25)

    assert len(chunks) > 1
    assert all(len(chunk) <= 25 for chunk in chunks)
    assert " ".join(chunks) == text


def test_split_text_for_tts_empty_text_raises_value_error():
    with pytest.raises(ValueError):
        split_text_for_tts("   ")
