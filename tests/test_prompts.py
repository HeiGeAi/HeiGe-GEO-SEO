import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import prompts  # noqa: E402


class TestPrompts(unittest.TestCase):
    def test_basic_generation(self):
        rows = prompts.generate("智能排版器", "公众号排版工具",
                                competitors=["壹伴"], problems=["排版费时"],
                                personas=["自媒体作者"])
        self.assertGreater(len(rows), 5)

    def test_no_residual_placeholders(self):
        rows = prompts.generate("Brand", "category")  # no problem/persona/etc
        for r in rows:
            self.assertNotIn("{", r["prompt"])
            self.assertNotIn("}", r["prompt"])

    def test_skips_templates_without_values(self):
        # without problems, no problem-aware prompt should appear
        rows = prompts.generate("Brand", "tools")
        intents = {r["intent"] for r in rows}
        self.assertNotIn("problem-aware", intents)

    def test_non_brand_first(self):
        rows = prompts.generate("Brand", "tools", competitors=["Rival"])
        first_brand = next((i for i, r in enumerate(rows) if r["brand_type"] == "brand"), len(rows))
        last_nonbrand = max((i for i, r in enumerate(rows) if r["brand_type"] == "non-brand"),
                            default=-1)
        self.assertLess(last_nonbrand, len(rows))
        # all non-brand come before brand
        self.assertTrue(all(rows[i]["brand_type"] == "non-brand" for i in range(first_brand)))

    def test_limit(self):
        rows = prompts.generate("B", "c", competitors=["X", "Y", "Z"], limit=3)
        self.assertEqual(len(rows), 3)

    def test_english(self):
        rows = prompts.generate("B", "tools", lang="en")
        self.assertTrue(all(r["lang"] == "en" for r in rows))

    def test_csv_and_json(self):
        rows = prompts.generate("B", "tools")
        self.assertIn("prompt", prompts.to_csv(rows))
        self.assertIn("prompts", prompts.to_json(rows))

    def test_samples_recommended(self):
        rows = prompts.generate("B", "tools")
        self.assertEqual(rows[0]["samples_recommended"], 3)


if __name__ == "__main__":
    unittest.main()
