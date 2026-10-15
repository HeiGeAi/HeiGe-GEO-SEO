"""Regressions for crawler exclusions and URL/file encoding boundaries."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import generators, internal_links  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = ("allow-all", "expose-only", "cn-index")


def groups(text):
    """Read our one-agent-per-group output, without wildcard inheritance."""
    result = {}
    current = None
    for line in text.splitlines():
        if line.startswith("User-agent: "):
            current = line.split(": ", 1)[1]
            result[current] = []
        elif line.startswith(("Allow: ", "Disallow: ")):
            result[current].append(line)
    return result


class TestRobotsGroupRestrictions(unittest.TestCase):
    def assert_exclusions(self, strategy, excluded):
        rendered = groups(generators.gen_robots(strategy, disallow_paths=excluded))
        for ua, rules in rendered.items():
            with self.subTest(strategy=strategy, ua=ua):
                if strategy == "expose-only" and ua in generators._AI_TRAIN_BOTS:
                    self.assertEqual(rules, ["Disallow: /"])
                else:
                    for path in excluded:
                        self.assertIn("Disallow: " + path, rules)
                    if "/" in excluded:
                        self.assertNotIn("Allow: /", rules)
                    else:
                        self.assertIn("Allow: /", rules)
        self.assertIn("*", rendered)
        self.assertIn("Googlebot", rendered)
        self.assertIn("OAI-SearchBot", rendered)

    def test_custom_exclusions_reach_every_named_and_wildcard_group(self):
        for strategy in STRATEGIES:
            self.assert_exclusions(strategy, ["/private/", "/drafts/"])

    def test_default_exclusions_reach_every_allowed_group(self):
        for strategy in STRATEGIES:
            self.assert_exclusions(strategy, ["/admin/", "/api/"])
            self.assertEqual(generators.gen_robots(strategy),
                             generators.gen_robots(strategy, disallow_paths=["/admin/", "/api/"]))

    def test_root_exclusion_is_not_cancelled_by_equal_allow_rule(self):
        for strategy in STRATEGIES:
            self.assert_exclusions(strategy, ["/", "/private/"])

    def test_cli_disallow_and_sitemap(self):
        for strategy in STRATEGIES:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/geo_cli.py"), "robots",
                 "--strategy", strategy, "--disallow", "/private/",
                 "--sitemap", "https://example.com/sitemap.xml"],
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Disallow: /private/", groups(result.stdout)["Googlebot"])
            self.assertEqual(result.stdout.count("Sitemap: https://example.com/sitemap.xml"), 1)


class TestInternalLinkEncoding(unittest.TestCase):
    def test_unicode_and_space_paths_match_encoded_links(self):
        result = internal_links.analyze([
            ("/index.html", '<a href="about%20us.html">A</a><a href="%e5%85%b3%e4%ba%8e.html">B</a>'),
            ("/about us.html", '<a href="index.html">Home</a>'),
            ("/关于.html", '<a href="index.html">Home</a>'),
        ], home="/index.html")
        self.assertEqual(result["orphan_count"], 0)
        self.assertEqual(result["internal_links_total"], 4)
        self.assertEqual(result["inbound_by_page"]["/about%20us.html"], 1)
        self.assertEqual(result["inbound_by_page"]["/%E5%85%B3%E4%BA%8E.html"], 1)

    def test_encoded_page_keys_match_raw_links_and_home(self):
        result = internal_links.analyze([
            ("/%e5%85%b3%e4%ba%8e.html", '<a href="about us.html">About</a>'),
            ("/about%20us.html", ""),
        ], home="/关于.html")
        self.assertEqual(result["orphan_count"], 0)
        self.assertEqual(result["inbound_by_page"]["/about%20us.html"], 1)

    def test_queries_fragments_hosts_and_nested_paths(self):
        result = internal_links.analyze([
            ("https://example.com/中文/index.html", '<a href="../about%20us.html?src=x#top">A</a>'),
            ("/about us.html", '<a href="//example.com/%E4%B8%AD%E6%96%87/index.html#top">Home</a>'
             '<a href="https://external.example/中文/index.html">External</a>'
             '<a href="#top">Self</a><a href="?page=1">Self</a>'),
        ], base_hosts=["example.com"], home="/中文/index.html")
        self.assertEqual(result["orphan_count"], 0)
        self.assertEqual(result["internal_links_total"], 2)

    def test_encoded_reserved_characters_stay_distinct(self):
        for escaped, literal in [("%2f", "/"), ("%3f", "?"), ("%23", "#"),
                                 ("%2b", "+"), ("%26", "&"), ("%3b", ";")]:
            with self.subTest(escaped=escaped):
                encoded = internal_links._norm("/a" + escaped + "b", set())
                self.assertEqual(encoded, "/a" + escaped.upper() + "b")
                self.assertNotEqual(encoded, internal_links._norm("/a" + literal + "b", set()))
        self.assertNotEqual(internal_links._page_key("/a%252Fb"),
                            internal_links._page_key("/a%2Fb"))

    def test_unreserved_escapes_and_hex_case_are_canonical(self):
        self.assertEqual(internal_links._page_key("/%7e%61%2Ehtml"), "/~a.html")
        self.assertEqual(internal_links._norm("/caf%c3%a9.html", set()), "/caf%C3%A9.html")
        self.assertEqual(internal_links._norm("/100% done.html", set()), "/100%25%20done.html")

    def test_encoded_slash_does_not_create_false_inbound(self):
        result = internal_links.analyze([
            ("/index.html", '<a href="/docs%2fguide.html">Encoded</a>'),
            ("/docs/guide.html", '<a href="/index.html">Home</a>'),
        ], home="/index.html")
        self.assertEqual(result["orphan_pages"], ["/docs/guide.html"])

    def test_directory_base_semantics_survive_encoding(self):
        result = internal_links.analyze([
            ("/中文/", '<a href="about%20us.html">About</a>'),
            ("/中文/about us.html", '<a href="./">Home</a>'),
        ], home="/中文/")
        self.assertEqual(result["orphan_count"], 0)

    def test_cli_files_with_unicode_spaces_and_literal_percent(self):
        filenames = ["about us.html", "关于.html", "about%20us.html", "docs%2Fguide.html", "topic#one.html"]
        if os.name != "nt":
            filenames.append("topic?one.html")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("".join(
                '<a href="%s?ref=test#top">Page</a>' % quote(name, safe="")
                for name in filenames), encoding="utf-8")
            for name in filenames:
                (root / name).write_text('<a href="index.html">Home</a>', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/geo_cli.py"), "internal-links",
                 "index.html", *filenames, "--root", str(root), "--home", "index.html"],
                cwd=root, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(data["pages"], len(filenames) + 1)
            self.assertEqual(data["orphan_count"], 0)
            for name in filenames:
                self.assertEqual(data["inbound_by_page"]["/" + quote(name, safe="")], 1)


if __name__ == "__main__":
    unittest.main()
