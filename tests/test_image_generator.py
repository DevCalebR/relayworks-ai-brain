import base64

from tools import image_generator
from tools.image_generator import (
    _build_image_prompt,
    generate_scene_images,
    sanitize_image_prompt_context,
)


class _ImageResponse:
    def __init__(self, image_bytes=b"fake png bytes"):
        self.data = [
            type(
                "ImageData",
                (),
                {"b64_json": base64.b64encode(image_bytes).decode("ascii")},
            )()
        ]


class _RetryImages:
    def __init__(self):
        self.prompts = []

    def generate(self, **kwargs):
        self.prompts.append(kwargs["prompt"])

        if len(self.prompts) == 1:
            raise RuntimeError("moderation_blocked safety violation")

        return _ImageResponse()


class _RetryClient:
    def __init__(self):
        self.images = _RetryImages()


def test_sanitize_image_prompt_context_softens_sensitive_documentary_terms():
    text = (
        "The missing children were trapped in a house fire. Investigators later "
        "searched for bodies, remains, and bones after a possible kidnapping. "
        "The family faced grief, violence, gore, and self-harm rumors."
    )

    sanitized = sanitize_image_prompt_context(
        text,
        topic="The Disappearance of the Sodder Children",
    )
    lowered = sanitized.lower()

    assert "vintage missing-person case file" in lowered
    assert "old house exterior at night" in lowered
    assert "archival investigation notes" in lowered
    assert "empty rural road" in lowered

    for unsafe_term in (
        "missing children",
        "children were trapped",
        "house fire",
        "bodies",
        "remains",
        "bones",
        "kidnapping",
        "violence",
        "gore",
        "self-harm",
    ):
        assert unsafe_term not in lowered


def test_build_image_prompt_includes_documentary_safety_constraints():
    prompt = _build_image_prompt(
        "The Disappearance of the Sodder Children",
        "The missing children were trapped in a house fire and remains were found.",
        template="ai",
        video_format="landscape",
    )
    lowered = prompt.lower()

    assert "documentary-style historical visual" in lowered
    assert "no children" in lowered
    assert "no bodies" in lowered
    assert "no gore" in lowered
    assert "no violence" in lowered
    assert "no active fire" in lowered
    assert "no distress" in lowered
    assert "no readable text" in lowered
    assert "no watermark" in lowered
    assert "the historical sodder family mystery" in lowered
    assert "sodder children" not in lowered
    assert "house fire" not in lowered
    assert "children were trapped" not in lowered
    assert "remains were found" not in lowered


def test_generate_scene_images_retries_moderation_with_safe_fallback(
    tmp_path,
    monkeypatch,
):
    client = _RetryClient()
    monkeypatch.setattr(image_generator, "_get_client", lambda: client)
    monkeypatch.setattr(image_generator, "IMAGES_OUTPUT_DIR", tmp_path)

    paths = generate_scene_images(
        topic="The Disappearance of the Sodder Children",
        narration_text="The missing children vanished after a house fire.",
        output_name="Manual Script Test",
        image_count=1,
        template="ai",
        video_format="landscape",
    )

    assert len(client.images.prompts) == 2
    assert "quiet 1940s Appalachian town at night" in client.images.prompts[1]
    assert "no children" in client.images.prompts[1]
    assert "no bodies" in client.images.prompts[1]
    assert "no active fire" in client.images.prompts[1]
    assert paths == [str(tmp_path / "manual-script-test-scene-01.png")]
    assert (tmp_path / "manual-script-test-scene-01.png").read_bytes() == b"fake png bytes"
