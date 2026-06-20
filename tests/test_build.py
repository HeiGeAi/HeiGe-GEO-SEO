import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build as build_mod  # noqa: E402

EXPECTED = ["claude-code", "codex", "openclaw", "hermes"]


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = build_mod.build()

    def test_all_adapters_built(self):
        for a in EXPECTED:
            self.assertIn(a, self.record["adapters"])

    def test_adapters_self_contained(self):
        for a in EXPECTED:
            pkg = os.path.join(ROOT, "adapters", a, "heige-geo-seo")
            self.assertTrue(os.path.isfile(os.path.join(pkg, "scripts", "geo_cli.py")),
                            "%s 缺 geo_cli.py" % a)
            self.assertTrue(os.path.isfile(os.path.join(pkg, "scripts", "lib", "scoring.py")))
            for d in ("knowledge", "methodology", "workflow", "templates"):
                self.assertTrue(os.path.isdir(os.path.join(pkg, d)), "%s 缺 %s" % (a, d))
            self.assertTrue(os.path.isfile(os.path.join(pkg, "manifest.json")))
            self.assertTrue(os.path.isfile(os.path.join(pkg, "INSTALL.md")))

    def test_entry_files_per_runtime(self):
        entries = {
            "claude-code": "SKILL.md",
            "codex": "AGENTS.md",
            "openclaw": "SKILL.md",
            "hermes": "skill.md",
        }
        for a, entry in entries.items():
            pkg = os.path.join(ROOT, "adapters", a, "heige-geo-seo")
            self.assertTrue(os.path.isfile(os.path.join(pkg, entry)),
                            "%s 缺入口 %s" % (a, entry))

    def test_build_manifest_written(self):
        bm = os.path.join(ROOT, "adapters", "build-manifest.json")
        self.assertTrue(os.path.isfile(bm))
        with open(bm, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(set(data["adapters"].keys()), set(EXPECTED))

    def test_build_is_deterministic(self):
        a = build_mod.build()
        b = build_mod.build()
        for adapter in EXPECTED:
            self.assertEqual(a["adapters"][adapter]["files"],
                             b["adapters"][adapter]["files"],
                             "%s 两次构建文件哈希不一致" % adapter)

    def test_knowledge_content_matches_source(self):
        src = open(os.path.join(ROOT, "source", "knowledge", "01-llm-landscape.md"),
                   encoding="utf-8").read()
        for a in EXPECTED:
            dst = open(os.path.join(ROOT, "adapters", a, "heige-geo-seo",
                                    "knowledge", "01-llm-landscape.md"),
                       encoding="utf-8").read()
            self.assertEqual(src, dst, "%s 知识库与源不一致" % a)


if __name__ == "__main__":
    unittest.main()
