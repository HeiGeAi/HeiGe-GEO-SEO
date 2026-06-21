import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, scoring, instruction, anti_ai  # noqa: E402


class TestInstructionCompiler(unittest.TestCase):
    def setUp(self):
        self.poor = htmldoc.from_file(_path.fixture("poor_page.html"))
        self.good = htmldoc.from_file(_path.fixture("good_page.html"))

    def test_poor_page_yields_instructions(self):
        score = scoring.score_document(self.poor)
        pack = instruction.compile_instructions(score)
        self.assertGreater(pack["instruction_count"], 0)
        first = pack["instructions"][0]
        self.assertIn("rewrite_instruction", first)
        self.assertIn("geo_method", first)
        self.assertIn("anti_ai_clause", first)

    def test_only_content_dims(self):
        score = scoring.score_document(self.poor)
        pack = instruction.compile_instructions(score)
        for ins in pack["instructions"]:
            self.assertIn(ins["dimension"], ("C", "D", "E", "F"))

    def test_sorted_by_weight_gap(self):
        score = scoring.score_document(self.poor)
        pack = instruction.compile_instructions(score)
        gaps = [p["weight"] - p["earned"] for p in pack["instructions"]]
        self.assertEqual(gaps, sorted(gaps, reverse=True))

    def test_engine_fork_added(self):
        score = scoring.score_document(self.poor)
        pack = instruction.compile_instructions(score, target_engine="perplexity")
        self.assertTrue(any("engine_fork" in p for p in pack["instructions"]))

    def test_render_markdown(self):
        score = scoring.score_document(self.poor)
        md = instruction.render_markdown(instruction.compile_instructions(score))
        self.assertIn("GEO 改写指令包", md)

    def test_brief_generation(self):
        brief = instruction.gen_geo_brief(
            "公众号排版", "公众号怎么快速排版", ["X 是什么", "怎么用"],
            entities=["智能排版器"], target_engine="豆包")
        self.assertEqual(len(brief["sections"]), 2)
        self.assertIn("engine_note", brief)
        md = instruction.render_brief_markdown(brief)
        self.assertIn("GEO Content Brief", md)


class TestAntiAi(unittest.TestCase):
    def test_detects_negative_contrast(self):
        f = anti_ai.scan("这不是一个工具而是一个平台")
        self.assertTrue(any(x["type"] == "否定对比句式" for x in f))

    def test_detects_dash_and_marketing(self):
        f = anti_ai.scan("我们赋能生态——实现闭环")
        types = {x["type"] for x in f}
        self.assertIn("营销词", types)
        self.assertIn("破折号", types)

    def test_clean_text_scores_high(self):
        self.assertEqual(anti_ai.score("这是一个排版工具,每月 39 元。"), 100)

    def test_constraint_clause(self):
        self.assertIn("反AI味约束", anti_ai.constraint_clause("zh"))


if __name__ == "__main__":
    unittest.main()
