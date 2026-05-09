import unittest

from agents.script_agent import _build_series_episode_script_messages


def _episode_source(episode_number=1, episode_count=5, previous_episode=None, next_episode=None):
    episode_plan = {
        "episode_number": episode_number,
        "title": "The Lighthouse Went Silent",
        "episode_topic": "The Flannan Isles Lighthouse disappearance",
        "chapter_summary": (
            "The relief vessel reaches the Flannan Isles lighthouse and finds the "
            "station empty even though three keepers were supposed to be there."
        ),
        "key_beats": [
            "The relief vessel approaches the dark lighthouse.",
            "The replacement keeper steps inside and finds the station empty.",
            "One set of oilskins appears to have been left behind.",
            "The west landing shows signs of storm damage.",
        ],
        "evidence_focus": [
            "Relief crew observations.",
            "Lighthouse log entries, if relevant.",
            "Later retellings, which should be treated carefully.",
        ],
        "continuity_from_previous": "The previous episode established the discovery.",
        "ending_tease": "The next episode asks what the weather can and cannot explain.",
        "next_episode_setup": "Next, the story turns to the storm and the landing.",
    }
    if episode_number == episode_count:
        episode_plan["final_closing_thought"] = (
            "The strongest explanation still leaves details the record cannot close."
        )

    return {
        "series_bible": {
            "series_title": "The Flannan Isles Lighthouse Mystery",
            "topic": "Flannan Isles Lighthouse Mystery",
            "episode_count": episode_count,
            "what_is_known": [
                "Three lighthouse keepers disappeared in December 1900.",
            ],
            "what_is_uncertain": [
                "The exact sequence of events is unknown.",
            ],
        },
        "episode_plan": episode_plan,
        "previous_episode": previous_episode,
        "next_episode": next_episode,
        "chapter_text": (
            "The episode opens with the relief vessel nearing the island, the "
            "lighthouse dark, and no one greeting the boat."
        ),
    }


def _prompt_text(episode_source):
    messages = _build_series_episode_script_messages(
        episode_source,
        target_duration_seconds=150,
    )
    return "\n".join(message["content"] for message in messages)


class SeriesEpisodeScriptPromptTests(unittest.TestCase):
    def test_first_episode_prompt_requires_discovery_opening(self):
        prompt = _prompt_text(
            _episode_source(
                episode_number=1,
                next_episode={"episode_number": 2, "title": "The Storm Clues"},
            )
        )

        self.assertIn("For Episode 1: start with the discovery", prompt)
        self.assertIn("central contradiction", prompt)
        self.assertIn("Do not start with generic atmosphere", prompt)
        self.assertIn("Put the viewer directly into the event", prompt)
        self.assertNotIn("For Episode 2 and later:", prompt)

    def test_later_episode_prompt_uses_continuity_not_full_recap(self):
        prompt = _prompt_text(
            _episode_source(
                episode_number=2,
                previous_episode={"episode_number": 1, "title": "The Discovery"},
                next_episode={"episode_number": 3, "title": "The Logbook"},
            )
        )

        self.assertIn("For Episode 2 and later:", prompt)
        self.assertIn("reconnecting to the previous episode in one sentence", prompt)
        self.assertIn("new clue, contradiction, or question", prompt)
        self.assertIn("Do not re-explain the entire series", prompt)
        self.assertNotIn("For Episode 1:", prompt)

    def test_final_episode_prompt_does_not_tease_fake_next_episode(self):
        prompt = _prompt_text(
            _episode_source(
                episode_number=5,
                episode_count=5,
                previous_episode={"episode_number": 4, "title": "The Theory"},
                next_episode=None,
            )
        )

        self.assertIn("Final episode ending:", prompt)
        self.assertIn("strongest grounded explanation", prompt)
        self.assertIn("what remains unknowable", prompt)
        self.assertIn("do not tease a fake next episode", prompt)

    def test_prompt_blocks_unsupported_psychology_language(self):
        prompt = _prompt_text(_episode_source())

        self.assertIn("No unsupported psychology rule", prompt)
        self.assertIn("inner demons", prompt)
        self.assertIn("dark corners of the mind", prompt)
        self.assertIn("thoughts nobody could know", prompt)
        self.assertIn("emotions nobody recorded", prompt)
        self.assertIn("psychological breakdown", prompt)
        self.assertIn("madness", prompt)
        self.assertIn("hallucinations", prompt)
        self.assertIn("secret motives", prompt)
        self.assertIn("isolation may have added pressure", prompt)
        self.assertIn("later retellings have imagined tension", prompt)
        self.assertIn("the evidence does not prove what they were thinking", prompt)

    def test_prompt_enforces_concrete_visual_details(self):
        prompt = _prompt_text(_episode_source())

        self.assertIn("Concrete detail rule", prompt)
        self.assertIn("Include several concrete, visual details", prompt)
        self.assertIn("relief vessel approaching the island", prompt)
        self.assertIn("dark lighthouse", prompt)
        self.assertIn("no one greeting the boat", prompt)
        self.assertIn("missing oilskins", prompt)
        self.assertIn("damaged landing", prompt)
        self.assertIn("later retellings changing the story", prompt)

    def test_prompt_enforces_narration_only_output(self):
        prompt = _prompt_text(_episode_source())

        self.assertIn("Produce narration-only output", prompt)
        self.assertIn("approximately 320-450 words", prompt)
        self.assertIn("Target word range for this episode: roughly 320-448 words", prompt)
        self.assertIn("No markdown", prompt)
        self.assertIn("No bullet points", prompt)
        self.assertIn("No speaker labels", prompt)
        self.assertIn("No timestamps", prompt)
        self.assertIn("No bracketed stage directions", prompt)
        self.assertIn("No camera directions", prompt)
        self.assertIn("No source citations inside the spoken script", prompt)
        self.assertIn("exactly one short natural call to action", prompt)
        self.assertIn("series episodes", prompt)


if __name__ == "__main__":
    unittest.main()
