import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import sov  # noqa: E402


class TestSov(unittest.TestCase):
    def test_parse_answer_positions(self):
        p = sov.parse_answer("先说 A,再说 B。", ["A", "B"])
        self.assertEqual(p["positions"]["A"], 1)
        self.assertEqual(p["positions"]["B"], 2)

    def test_parse_citations(self):
        p = sov.parse_answer("见 https://a.com/x 和 http://b.org", ["A"])
        self.assertIn("a.com", p["citations"])
        self.assertIn("b.org", p["citations"])

    def test_mention_sov(self):
        recs = [
            {"prompt": "q1", "engine": "e", "answer": "推荐 Acme 和 Rival"},
            {"prompt": "q2", "engine": "e", "answer": "只推荐 Acme"},
        ]
        r = sov.analyze(recs, "Acme", ["Rival"])
        # Acme appears twice, Rival once -> 2/3
        self.assertAlmostEqual(r["mention_sov"]["Acme"], 66.7, delta=0.2)

    def test_weighted_sov_position(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "Acme 第一,Rival 第二"}]
        r = sov.analyze(recs, "Acme", ["Rival"])
        # Acme pos1=1.0, Rival pos2=0.5 -> 1/1.5 = 66.7
        self.assertGreater(r["weighted_sov"]["Acme"], r["weighted_sov"]["Rival"])

    def test_citation_sov(self):
        recs = [{"prompt": "q", "engine": "e",
                 "answer": "见 https://acme.com/a 和 https://rival.com/b"}]
        r = sov.analyze(recs, "Acme", ["Rival"], brand_domain="acme.com",
                        competitor_domains={"Rival": "rival.com"})
        self.assertEqual(r["citation_sov"]["Acme"], 50.0)

    def test_alias_merge(self):
        recs = [{"prompt": "q", "engine": "e", "answer": "艾克米很好"}]
        r = sov.analyze(recs, "Acme", aliases={"Acme": ["艾克米"]})
        self.assertEqual(r["coverage"]["hit"], 1)

    def test_sampling_instability_flagged(self):
        recs = [
            {"prompt": "q", "engine": "e", "answer": "Acme 好"},
            {"prompt": "q", "engine": "e", "answer": "没提到"},
        ]
        r = sov.analyze(recs, "Acme")
        self.assertEqual(len(r["sampling"]["unstable_prompts"]), 1)

    def test_tier_classification(self):
        self.assertEqual(sov.classify_tier(50, 40), "领导者")
        self.assertEqual(sov.classify_tier(5, 3), "新进入者")

    def test_per_engine_breakdown(self):
        recs = [
            {"prompt": "q", "engine": "doubao", "answer": "Acme"},
            {"prompt": "q", "engine": "yuanbao", "answer": "Rival"},
        ]
        r = sov.analyze(recs, "Acme", ["Rival"])
        self.assertIn("doubao", r["per_engine_mention_sov"])
        self.assertIn("yuanbao", r["per_engine_mention_sov"])


if __name__ == "__main__":
    unittest.main()
