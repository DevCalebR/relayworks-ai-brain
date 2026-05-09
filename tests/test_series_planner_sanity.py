import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import series_planner
from tools.series_planner import (
    DEFAULT_SUGGESTED_IMAGE_COUNT,
    DEFAULT_SUGGESTED_VIDEO_FORMAT,
    _normalize_series_plan,
    _validate_series_plan,
    save_series_plan,
    validate_series_plan_quality,
)


def _base_plan(episode):
    return {
        "series_title": "The Flannan Isles Lighthouse Mystery",
        "topic": "Flannan Isles Lighthouse Mystery",
        "audience": "mystery viewers",
        "target_duration_seconds": 150,
        "episode_count": 1,
        "tone": "careful and eerie",
        "factual_guardrails": ["Do not invent evidence."],
        "series_narrative_arc": (
            "The series begins with the disappearance, escalates through the record, "
            "and ends by naming what remains unresolved."
        ),
        "what_is_known": ["Three lighthouse keepers disappeared in December 1900."],
        "what_is_uncertain": ["The exact sequence of events is unknown."],
        "what_not_to_claim": ["Do not claim unsupported notes or vessels existed."],
        "source_sensitivity_notes": [
            "Later retellings exaggerate some details; keep claims qualified.",
        ],
        "key_people_or_groups": ["The lighthouse keepers"],
        "timeline": ["December 1900: the keepers were found missing."],
        "episode_plan": [episode],
    }


def _base_episode(**overrides):
    episode = {
        "episode_number": 1,
        "title": "The Lighthouse Went Silent",
        "episode_topic": "The disappearance at the Flannan Isles lighthouse",
        "hook": "Three keepers vanished from a remote lighthouse.",
        "chapter_summary": (
            "The episode stays with the documented disappearance and uses careful "
            "wording around what the record can prove."
        ),
        "key_beats": [
            "The relief party reaches the lighthouse.",
            "The keepers are missing.",
            "The record leaves key questions unresolved.",
            "Later retellings add unsupported drama.",
            "The case moves into competing explanations.",
        ],
        "continuity_from_previous": "",
        "ending_tease": "The next episode follows the timeline before the disappearance.",
        "next_episode_setup": "The timeline before the keepers vanished.",
        "suggested_template": "ai",
        "suggested_image_count": 12,
        "suggested_thumbnail_angle": "Remote lighthouse exterior",
        "suggested_video_format": "landscape",
        "evidence_focus": ["The missing keepers", "The lighthouse location"],
        "avoid_repeating": [],
    }
    episode.update(overrides)
    return episode


def _episode_list(count, **overrides):
    episodes = []
    for index in range(1, count + 1):
        episode_overrides = {
            "episode_number": index,
            "title": f"The Lighthouse Went Silent Part {index}",
        }
        episode_overrides.update(overrides)
        episodes.append(_base_episode(**episode_overrides))
    return episodes


class SeriesPlannerSanityTests(unittest.TestCase):
    def test_flannan_empty_ship_episode_is_normalized(self):
        plan = _base_plan(
            _base_episode(
                title="The Empty Ship Found Drifting",
                episode_topic="The documented lighthouse disappearance",
                chapter_summary=(
                    "Joseph Moore found cryptic notes inside a perfectly untouched "
                    "lighthouse after an empty ship appeared nearby."
                ),
                ending_tease="Next, the cryptic notes reveal another clue.",
                evidence_focus=[
                    "empty ship",
                    "drifting vessel",
                    "lifeboat",
                    "expert opinions",
                    "The lighthouse location",
                ],
                suggested_template="mystery_build-up",
                suggested_image_count=None,
                suggested_video_format=None,
            )
        )

        normalized = _normalize_series_plan(plan)
        episode = normalized["episode_plan"][0]

        self.assertEqual(episode["title"], "The documented lighthouse disappearance")
        self.assertEqual(episode["evidence_focus"], ["The lighthouse location"])
        self.assertNotIn("cryptic notes", episode["chapter_summary"].lower())
        self.assertNotIn("cryptic notes", episode["ending_tease"].lower())
        self.assertIn("no obvious signs of violence", episode["chapter_summary"])
        _validate_series_plan(normalized)

    def test_invalid_template_defaults_to_ai(self):
        plan = _base_plan(_base_episode(suggested_template="custom-template"))

        normalized = _normalize_series_plan(plan)

        self.assertEqual(normalized["episode_plan"][0]["suggested_template"], "ai")

    def test_missing_image_count_defaults_to_12(self):
        plan = _base_plan(_base_episode(suggested_image_count=None))

        normalized = _normalize_series_plan(plan)

        self.assertEqual(
            normalized["episode_plan"][0]["suggested_image_count"],
            DEFAULT_SUGGESTED_IMAGE_COUNT,
        )

    def test_missing_video_format_defaults_to_landscape(self):
        plan = _base_plan(_base_episode(suggested_video_format=None))

        normalized = _normalize_series_plan(plan)

        self.assertEqual(
            normalized["episode_plan"][0]["suggested_video_format"],
            DEFAULT_SUGGESTED_VIDEO_FORMAT,
        )

    def test_missing_top_level_guardrails_are_normalized(self):
        plan = _base_plan(_base_episode())
        plan["episode_plan"] = _episode_list(5)
        del plan["what_is_known"]
        del plan["what_is_uncertain"]
        del plan["what_not_to_claim"]
        del plan["factual_guardrails"]
        del plan["source_sensitivity_notes"]
        del plan["key_people_or_groups"]
        del plan["timeline"]
        del plan["tone"]
        del plan["audience"]
        del plan["target_duration_seconds"]
        del plan["episode_count"]
        del plan["topic"]
        del plan["series_title"]

        normalized = _normalize_series_plan(
            plan,
            topic="The Dancing Plague of 1518",
            episodes=5,
            target_duration_seconds=150,
            audience="fans of weird history and strange true stories",
        )

        self.assertEqual(normalized["series_title"], "The Dancing Plague of 1518")
        self.assertEqual(normalized["topic"], "The Dancing Plague of 1518")
        self.assertEqual(
            normalized["audience"],
            "fans of weird history and strange true stories",
        )
        self.assertEqual(normalized["target_duration_seconds"], 150)
        self.assertEqual(normalized["episode_count"], 5)
        self.assertTrue(normalized["what_is_known"])
        self.assertTrue(normalized["what_is_uncertain"])
        self.assertTrue(normalized["what_not_to_claim"])
        self.assertTrue(normalized["factual_guardrails"])
        self.assertTrue(normalized["source_sensitivity_notes"])
        self.assertEqual(normalized["key_people_or_groups"], [])
        self.assertEqual(normalized["timeline"], [])
        _validate_series_plan(normalized, expected_episodes=5)

    def test_missing_episode_plan_still_fails_validation(self):
        plan = _base_plan(_base_episode())
        del plan["episode_plan"]

        normalized = _normalize_series_plan(
            plan,
            topic="The Dancing Plague of 1518",
            episodes=5,
            target_duration_seconds=150,
            audience="fans of weird history and strange true stories",
        )

        with self.assertRaisesRegex(
            ValueError,
            "Series plan episode_plan must be a non-empty list",
        ):
            _validate_series_plan(normalized)

    def test_requested_episode_count_mismatch_fails_validation(self):
        plan = _base_plan(_base_episode())
        plan["episode_count"] = 5
        plan["episode_plan"] = _episode_list(4)

        normalized = _normalize_series_plan(
            plan,
            topic="The Dancing Plague of 1518",
            episodes=5,
            target_duration_seconds=150,
            audience="fans of weird history and strange true stories",
        )

        with self.assertRaisesRegex(
            ValueError,
            "Series plan expected 5 episodes but got 4",
        ):
            _validate_series_plan(normalized, expected_episodes=5)

    def test_requested_episode_count_match_passes_validation(self):
        plan = _base_plan(_base_episode())
        plan["episode_count"] = 5
        plan["episode_plan"] = _episode_list(5)

        normalized = _normalize_series_plan(
            plan,
            topic="The Dancing Plague of 1518",
            episodes=5,
            target_duration_seconds=150,
            audience="fans of weird history and strange true stories",
        )

        self.assertEqual(len(normalized["episode_plan"]), 5)
        _validate_series_plan(normalized, expected_episodes=5)

    def test_bad_episode_numbers_normalize_when_count_matches(self):
        plan = _base_plan(_base_episode())
        plan["episode_count"] = 5
        plan["episode_plan"] = _episode_list(5, episode_number=None)

        normalized = _normalize_series_plan(
            plan,
            topic="The Dancing Plague of 1518",
            episodes=5,
            target_duration_seconds=150,
            audience="fans of weird history and strange true stories",
        )

        self.assertEqual(
            [episode["episode_number"] for episode in normalized["episode_plan"]],
            [1, 2, 3, 4, 5],
        )
        _validate_series_plan(normalized, expected_episodes=5)

    def test_missing_series_narrative_arc_is_normalized(self):
        plan = _base_plan(_base_episode())
        del plan["series_narrative_arc"]

        normalized = _normalize_series_plan(plan)

        self.assertTrue(normalized["series_narrative_arc"])
        _validate_series_plan(normalized)

    def test_story_job_defaults_for_episode(self):
        plan = _base_plan(_base_episode())

        normalized = _normalize_series_plan(plan)

        self.assertIn("strongest hook", normalized["episode_plan"][0]["story_job"])
        _validate_series_plan(normalized)

    def test_generic_and_sensational_title_is_repaired(self):
        plan = _base_plan(
            _base_episode(
                title="Dancing Until Dead",
                episode_topic="What the Records Actually Say",
            )
        )

        normalized = _normalize_series_plan(plan)

        self.assertEqual(
            normalized["episode_plan"][0]["title"],
            "What the Records Actually Say",
        )
        _validate_series_plan(normalized)

    def test_generic_evidence_focus_is_filtered(self):
        plan = _base_plan(
            _base_episode(
                evidence_focus=[
                    "scholarly articles",
                    "expert opinions",
                    "expert commentary",
                    "modern theories",
                    "official sentiment",
                    "city council response",
                ]
            )
        )

        normalized = _normalize_series_plan(plan)

        self.assertEqual(
            normalized["episode_plan"][0]["evidence_focus"],
            ["city council response"],
        )
        _validate_series_plan(normalized)

    def test_final_episode_gets_closing_thought(self):
        plan = _base_plan(_base_episode())
        plan["episode_count"] = 5
        plan["episode_plan"] = _episode_list(5)
        plan["episode_plan"][-1]["final_closing_thought"] = None

        normalized = _normalize_series_plan(
            plan,
            topic="The Dancing Plague of 1518",
            episodes=5,
            target_duration_seconds=150,
            audience="fans of weird history and strange true stories",
        )

        self.assertNotIn("final_closing_thought", normalized["episode_plan"][0])
        self.assertIn(
            "records can narrow",
            normalized["episode_plan"][-1]["final_closing_thought"],
        )
        _validate_series_plan(normalized, expected_episodes=5)

    def test_quality_validation_flags_weak_series_plan(self):
        plan = _base_plan(
            _base_episode(
                title="The Evidence",
                hook="What really happened?",
                evidence_focus=["experts say the records show a mystery"],
                key_beats=["discussion", "Expert opinions"],
            )
        )

        report = validate_series_plan_quality(plan)

        self.assertFalse(report["ready_for_batch"])
        self.assertTrue(
            any("generic title" in issue for issue in report["issues"]),
            report["issues"],
        )
        self.assertTrue(
            any("weak hook" in issue for issue in report["issues"]),
            report["issues"],
        )
        self.assertTrue(
            any("fake-source" in issue for issue in report["issues"]),
            report["issues"],
        )
        self.assertTrue(
            any("vague key beat wording: discussion" in issue for issue in report["issues"]),
            report["issues"],
        )

    def test_quality_validation_flags_analysis_of_key_beat(self):
        plan = _base_plan(
            _base_episode(
                key_beats=["Analysis of the logbook entries and weather clues."],
            )
        )

        report = validate_series_plan_quality(plan)

        self.assertFalse(report["ready_for_batch"])
        self.assertTrue(
            any("vague key beat wording: analysis of" in issue for issue in report["issues"]),
            report["issues"],
        )

    def test_quality_validation_flags_overview_of_key_beat(self):
        plan = _base_plan(
            _base_episode(
                key_beats=["Overview of the lighthouse mystery."],
            )
        )

        report = validate_series_plan_quality(plan)

        self.assertFalse(report["ready_for_batch"])
        self.assertTrue(
            any("vague key beat wording: overview of" in issue for issue in report["issues"]),
            report["issues"],
        )

    def test_quality_validation_normalizes_unsupported_values_for_review(self):
        plan = _base_plan(
            _base_episode(
                suggested_template="mystery_build-up",
                suggested_video_format="cinematic",
            )
        )

        report = validate_series_plan_quality(plan)

        self.assertFalse(report["ready_for_batch"])
        self.assertEqual(plan["episode_plan"][0]["suggested_template"], "ai")
        self.assertEqual(plan["episode_plan"][0]["suggested_video_format"], "landscape")
        self.assertTrue(report["warnings"])

    def test_missing_final_episode_fields_are_normalized(self):
        plan = _base_plan(_base_episode())
        plan["episode_count"] = 2
        plan["episode_plan"] = _episode_list(2)
        final_episode = plan["episode_plan"][-1]
        del final_episode["ending_tease"]
        del final_episode["next_episode_setup"]
        del final_episode["suggested_thumbnail_angle"]

        normalized = _normalize_series_plan(plan, episodes=2)
        normalized_final = normalized["episode_plan"][-1]

        self.assertTrue(normalized_final["ending_tease"])
        self.assertIn("still leaves", normalized_final["ending_tease"])
        self.assertEqual(
            normalized_final["next_episode_setup"],
            "Series conclusion: leave viewers with the strongest grounded explanation and the mystery that remains.",
        )
        self.assertTrue(normalized_final["suggested_thumbnail_angle"])

    def test_quality_validation_flags_missing_final_ending_tease(self):
        plan = _base_plan(_base_episode())
        del plan["episode_plan"][0]["ending_tease"]

        report = validate_series_plan_quality(plan)

        self.assertFalse(report["ready_for_batch"])
        self.assertTrue(
            any("missing required field: ending_tease" in issue for issue in report["issues"]),
            report["issues"],
        )

    def test_final_episode_can_pass_with_fallback_style_next_setup(self):
        plan = _base_plan(
            _base_episode(
                hook=(
                    "When the relief crew reached the lighthouse, the lamps were dark, "
                    "the keepers were gone, and the sea had left almost no answers behind."
                ),
                chapter_summary=(
                    "The episode opens with the relief crew arriving at the lighthouse "
                    "and finding the keepers missing. The story stays with the documented "
                    "disappearance, the isolated location, the limited record, and the "
                    "careful difference between what was found and what later retellings "
                    "made more dramatic."
                ),
                key_beats=[
                    "The relief vessel approaches the dark lighthouse.",
                    "The first keeper steps inside and finds the living quarters empty.",
                    "The missing oilskins raise questions about whether the men went outside.",
                    "The damaged west landing suggests the sea may have reached higher than expected.",
                    "Later retellings turn uncertain details into legend.",
                    "The strongest theory explains one clue but leaves another unresolved.",
                ],
                narrative_purpose=(
                    "Close with the strongest grounded explanation and the question "
                    "the surviving record still cannot answer."
                ),
                avoid_repeating=[
                    "Do not repeat the full discovery setup except in one sentence.",
                ],
                continuity_from_previous="Series opener: begin with the central mystery.",
                ending_tease=(
                    "Even after the strongest explanation, the lighthouse still leaves "
                    "one question the surviving record cannot close."
                ),
                next_episode_setup=(
                    "Series conclusion: leave viewers with the strongest grounded "
                    "explanation and the mystery that remains."
                ),
                suggested_thumbnail_angle="Dark lighthouse over a violent sea.",
            )
        )
        plan["series_narrative_arc"] = (
            "The mystery begins with the relief vessel reaching a silent lighthouse, "
            "then escalates through the empty rooms, the weather-damaged landing, and "
            "the limited official record. The central tension is what the physical clues "
            "can explain versus what later retellings turned into legend, ending with "
            "the strongest grounded theory and the question that remains unknown."
        )

        report = validate_series_plan_quality(plan)

        self.assertTrue(report["ready_for_batch"], report["issues"])

    def test_concrete_visual_key_beats_pass_quality_check(self):
        plan = _base_plan(
            _base_episode(
                hook=(
                    "When the relief crew reached the lighthouse, the lamps were dark, "
                    "the keepers were gone, and the sea had left almost no answers behind."
                ),
                chapter_summary=(
                    "The episode opens with the relief crew crossing toward the isolated "
                    "lighthouse and finding empty rooms where three men should have been. "
                    "The story stays grounded in the documented disappearance, the hard "
                    "weather, and the clues that made the surviving record difficult to close."
                ),
                key_beats=[
                    "The relief vessel approaches the dark lighthouse.",
                    "The first man steps inside and finds the rooms empty.",
                    "The missing oilskins raise questions about whether the keepers went outside.",
                    "The damaged landing suggests the sea may have reached higher than expected.",
                    "The logbook entries make the final days feel more confusing.",
                    "Later retellings turn uncertain details into legend.",
                ],
                narrative_purpose=(
                    "Open with the eerie discovery and establish the grounded mystery."
                ),
                avoid_repeating=[
                    "Do not repeat later theories before the physical clues are established.",
                ],
                continuity_from_previous="Series opener: establish the central disappearance.",
            )
        )
        plan["series_narrative_arc"] = (
            "The mystery begins with the relief vessel reaching a silent lighthouse, "
            "escalates through the empty rooms, damaged landing, and uncertain logbook "
            "details, and ends by separating the grounded evidence from the legend that "
            "grew around the missing keepers."
        )

        report = validate_series_plan_quality(plan)

        self.assertTrue(report["ready_for_batch"], report["issues"])

    def test_save_series_plan_writes_quality_report(self):
        plan = _base_plan(
            _base_episode(
                hook=(
                    "When the relief crew reached the lighthouse, the lamps were dark, "
                    "the keepers were gone, and the sea had left almost no answers behind."
                ),
                chapter_summary=(
                    "The episode opens with the relief crew arriving at the lighthouse "
                    "and finding the keepers missing. The story stays grounded in the "
                    "documented disappearance, the isolated location, and the careful "
                    "limits of what the record can prove. The tension builds around what "
                    "was found, what was not found, and why later retellings made the case "
                    "sound cleaner than the evidence allows."
                ),
            )
        )
        plan["series_narrative_arc"] = (
            "The mystery begins with the silent lighthouse, escalates through the "
            "limited record and later retellings, keeps tension around what can be "
            "proved versus what people repeated, and ends by naming what the official "
            "record still cannot explain."
        )
        normalized = _normalize_series_plan(plan)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(series_planner, "SERIES_OUTPUT_DIR", Path(temp_dir)):
                saved_paths = save_series_plan(normalized)

            quality_path = Path(saved_paths["quality_report_path"])
            self.assertTrue(quality_path.exists())
            report = json.loads(quality_path.read_text(encoding="utf-8"))

        self.assertIn("ready_for_batch", report)
        self.assertIn("issues", report)
        self.assertIn("warnings", report)
        self.assertIn("suggestions", report)


if __name__ == "__main__":
    unittest.main()
