import unittest

from tools.text_cleaner import ensure_call_to_action


FALLBACK_CTA = (
    "If you want more strange stories like this, like this video and subscribe."
)


class TextCleanerCallToActionTests(unittest.TestCase):
    def test_subscribe_only_cta_is_replaced(self):
        self.assertEqual(
            ensure_call_to_action("This story is still unsolved. Subscribe for more."),
            f"This story is still unsolved. {FALLBACK_CTA}",
        )

    def test_like_only_cta_is_replaced(self):
        self.assertEqual(
            ensure_call_to_action(
                "This story is still unsolved. Like this video for more."
            ),
            f"This story is still unsolved. {FALLBACK_CTA}",
        )

    def test_existing_complete_final_cta_is_unchanged(self):
        narration = f"This story is still unsolved. {FALLBACK_CTA}"

        self.assertEqual(ensure_call_to_action(narration), narration)

    def test_duplicate_ctas_keep_one_at_the_end(self):
        self.assertEqual(
            ensure_call_to_action(
                "Subscribe for more. This story is still unsolved. Like and subscribe."
            ),
            "This story is still unsolved. Like and subscribe.",
        )

    def test_old_ai_business_cta_is_removed(self):
        self.assertEqual(
            ensure_call_to_action(
                "This story is still unsolved. If this helped, like this video "
                "and subscribe for more AI business ideas."
            ),
            f"This story is still unsolved. {FALLBACK_CTA}",
        )


if __name__ == "__main__":
    unittest.main()
