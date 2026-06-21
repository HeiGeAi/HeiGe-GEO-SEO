import json
import os
import sys
import unittest
import xml.dom.minidom as minidom

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import generators  # noqa: E402


class TestEntitySchema(unittest.TestCase):
    def test_organization_has_id_and_sameas(self):
        node = generators.gen_organization(
            "Acme", url="https://acme.com", logo="https://acme.com/l.png",
            same_as=["https://wikidata.org/wiki/Q1"])
        self.assertEqual(node["@type"], "Organization")
        self.assertTrue(node["@id"].endswith("/#org"))
        self.assertEqual(node["logo"]["@type"], "ImageObject")
        self.assertIn("https://wikidata.org/wiki/Q1", node["sameAs"])
        json.dumps(node)

    def test_person_schema(self):
        node = generators.gen_person("张三", job_title="CTO",
                                     url="https://x.com/about#a",
                                     knows_about=["SEO"], works_for="Acme")
        self.assertEqual(node["@id"], "https://x.com/about#a")
        self.assertEqual(node["worksFor"]["name"], "Acme")

    def test_website_schema(self):
        node = generators.gen_website("Acme", "https://acme.com", publisher="Acme Inc")
        self.assertTrue(node["@id"].endswith("/#website"))


class TestAiFiles(unittest.TestCase):
    def test_ai_txt_blocks_training_by_default(self):
        out = generators.gen_ai_txt(allow_train=False)
        self.assertIn("User-Agent: GPTBot", out)
        self.assertIn("train=no", out)
        self.assertIn("Citation: required", out)

    def test_robots_patch_is_diff(self):
        out = generators.gen_robots_patch()
        self.assertTrue(out.startswith("--- a/robots.txt"))
        self.assertIn("+User-agent: GPTBot", out)

    def test_sitemap_valid_xml(self):
        out = generators.gen_sitemap([("https://x.com/", "2026-06-21"), "https://x.com/a"])
        minidom.parseString(out)  # raises if invalid
        self.assertIn("<lastmod>2026-06-21</lastmod>", out)

    def test_answers_json(self):
        out = generators.gen_answers_json([("问", "答", "https://x.com/u"), ("q2", "a2")])
        data = json.loads(out)
        self.assertEqual(len(data["answers"]), 2)
        self.assertEqual(data["answers"][0]["url"], "https://x.com/u")

    def test_citations_json(self):
        out = generators.gen_citations_json([{"claim": "c", "source": "s", "date": "2026"}])
        data = json.loads(out)
        self.assertEqual(data["citations"][0]["id"], 1)

    def test_humans_txt(self):
        out = generators.gen_humans_txt(team=[("CTO", "Blake")], site="Acme")
        self.assertIn("CTO: Blake", out)

    def test_feed_xml_valid(self):
        out = generators.gen_feed_xml("T", "https://x.com",
                                      [("item", "Sat, 21 Jun 2026 00:00:00 GMT")])
        minidom.parseString(out)
        self.assertIn("<item>", out)


if __name__ == "__main__":
    unittest.main()
