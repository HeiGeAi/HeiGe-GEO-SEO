import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import attribution, agent_readiness, htmldoc  # noqa: E402


class TestAttribution(unittest.TestCase):
    def test_ga4_regex_has_engines(self):
        rx = attribution.gen_ga4_regex()
        self.assertIn("chatgpt", rx)
        self.assertIn("doubao", rx)
        self.assertIn("perplexity", rx)

    def test_utm(self):
        u = attribution.gen_utm("https://x.com/p", "chatgpt")
        self.assertIn("utm_source=llm", u)
        self.assertIn("utm_content=chatgpt", u)

    def test_utm_respects_existing_query(self):
        u = attribution.gen_utm("https://x.com/p?a=1", "claude")
        self.assertIn("?a=1&utm_source", u)

    def test_parse_access_log(self):
        log = (
            '1.2.3.4 - - [21/Jun/2026:00:00:00 +0000] "GET /a HTTP/1.1" 200 100 "-" '
            '"Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot)"\n'
            '1.2.3.5 - - [21/Jun/2026:00:00:01 +0000] "GET /b HTTP/1.1" 200 200 "-" '
            '"Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai)"\n'
        )
        r = attribution.parse_access_log(log)
        self.assertEqual(r["bots_seen"], 2)
        self.assertEqual(r["total_ai_hits"], 2)
        bots = {b["bot"] for b in r["by_bot"]}
        self.assertIn("GPTBot", bots)
        self.assertIn("PerplexityBot", bots)

    def test_region_and_purpose_classification(self):
        log = (
            '1.1.1.1 - - [x] "GET /a HTTP/1.1" 200 1 "-" "x GPTBot/1.3 y"\n'
            '1.1.1.2 - - [x] "GET /b HTTP/1.1" 200 1 "-" "x Baiduspider/2.0 y"\n'
            '1.1.1.3 - - [x] "GET /c HTTP/1.1" 200 1 "-" "x ChatGPT-User/1.0 y"\n'
        )
        r = attribution.parse_access_log(log)
        self.assertEqual(r["by_region"]["overseas"], 2)
        self.assertEqual(r["by_region"]["cn"], 1)
        self.assertEqual(r["by_purpose"]["train"], 1)
        self.assertEqual(r["by_purpose"]["user"], 1)
        self.assertEqual(r["realtime_read_hits"], 1)

    def test_blindspots_reported(self):
        r = attribution.parse_access_log("")
        self.assertTrue(any("Grok" in b for b in r["blindspots"]))

    def test_ga4_regex_has_cn_and_overseas(self):
        rx = attribution.gen_ga4_regex()
        self.assertIn("doubao", rx)
        self.assertIn("grok", rx)
        self.assertIn("perplexity", rx)
        self.assertIn("aisearchindex", rx)


class TestAgentReadiness(unittest.TestCase):
    def test_no_form_low_score(self):
        doc = htmldoc.from_string("<html><body><div>no form</div></body></html>")
        r = agent_readiness.audit(doc)
        self.assertLess(r["score"], 50)
        self.assertEqual(r["grade"], "未就绪")

    def test_good_form_high_score(self):
        html = (
            '<html><body><form toolname="checkout" tooldescription="buy now" '
            'aria-label="checkout">'
            '<label for="email">Email</label><input name="email" id="email">'
            '<button>购买</button></form></body></html>')
        doc = htmldoc.from_string(html)
        r = agent_readiness.audit(doc)
        self.assertGreaterEqual(r["score"], 80)
        self.assertEqual(r["grade"], "就绪")


if __name__ == "__main__":
    unittest.main()
