import json

from tools import metadata as metadata_module
from tools.metadata import (
    CTA_LINE,
    build_topic_hashtags,
    build_topic_tags,
    build_video_description,
    save_video_metadata,
)


FORBIDDEN_DEFAULT_DESCRIPTION_PHRASES = (
    "short",
    "quick video",
    "quick short",
    "in this quick short",
    "ai-generated",
    "generated locally",
    "relayworks ai content brain",
)


def test_episode_description_uses_polished_structure_without_shorts_language():
    topic = "The Lost Colony of Roanoke Episode 1: The Village That Vanished"

    description = build_video_description(topic)
    paragraphs = description.split("\n\n")
    lowered = description.lower()

    assert len(paragraphs) == 5
    assert "empty settlement" in paragraphs[0].lower()
    assert "croatoan clue" in paragraphs[1].lower()
    assert "part of a series" in paragraphs[2].lower()
    assert paragraphs[3] == CTA_LINE
    assert paragraphs[4].startswith("#Roanoke")
    assert paragraphs[4] == " ".join(build_topic_hashtags(topic))

    for phrase in FORBIDDEN_DEFAULT_DESCRIPTION_PHRASES:
        assert phrase not in lowered


def test_generic_episode_topic_mentions_series_when_episode_is_present():
    topic = "The Vanishing Village Episode 2: The Door Left Open"

    description = build_video_description(topic)

    assert "part of a series" in description.lower()
    assert "This episode covers the setting, timeline, key evidence" in description
    assert CTA_LINE in description


def test_topic_tags_and_hashtags_include_niche_specific_terms():
    roanoke_tags = build_topic_tags(
        "The Lost Colony of Roanoke Episode 1: The Village That Vanished"
    )
    flannan_tags = build_topic_tags("The Flannan Isles Lighthouse Mystery")
    mary_hashtags = build_topic_hashtags("The Mary Celeste Mystery")
    dancing_hashtags = build_topic_hashtags("The Dancing Plague of 1518")

    assert "history" in roanoke_tags
    assert "mystery" in roanoke_tags
    assert "weird history" in roanoke_tags
    assert "dark history" in roanoke_tags
    assert "unsolved mystery" in roanoke_tags
    assert "historical mystery" in roanoke_tags
    assert "eerie true stories" in roanoke_tags
    assert "strange history" in roanoke_tags
    assert "Roanoke" in roanoke_tags
    assert "Lost Colony" in roanoke_tags
    assert "Croatoan" in roanoke_tags
    assert "Flannan Isles" in flannan_tags
    assert "#MaryCeleste" in mary_hashtags
    assert "#DancingPlague" in dancing_hashtags
    assert 4 <= len(mary_hashtags) <= 6
    assert 4 <= len(dancing_hashtags) <= 6


def test_save_video_metadata_keeps_upload_compatible_json(tmp_path, monkeypatch):
    monkeypatch.setattr(metadata_module, "METADATA_OUTPUT_DIR", tmp_path)
    topic = "The Lost Colony of Roanoke Episode 1: The Village That Vanished"

    metadata_path = save_video_metadata(
        topic,
        script="The colony vanished, and the surviving record leaves questions.",
        output_name=topic,
    )
    output_path = (
        tmp_path
        / "the-lost-colony-of-roanoke-episode-1-the-village-that-vanished.json"
    )
    data = json.loads(output_path.read_text())

    assert metadata_path.endswith(
        "the-lost-colony-of-roanoke-episode-1-the-village-that-vanished.json"
    )
    assert {
        "title",
        "description",
        "tags",
        "hashtags",
        "topic",
        "generated_from",
    }.issubset(data)
    assert data["title"] == topic
    assert data["topic"] == topic
    assert data["generated_from"] == metadata_module.GENERATED_FROM
    assert data["description"].endswith(" ".join(data["hashtags"]))
    assert CTA_LINE in data["description"]
