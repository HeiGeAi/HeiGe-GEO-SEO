import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _path  # noqa: E402
from lib import htmldoc, diagnose  # noqa: E402


class TestDiagnose(unittest.TestCase):
    def test_good_page_few_failures(self):
        doc = htmldoc.from_file(_path.fixture("good_page.html"))
        r = diagnose.diagnose(doc)
        self.assertLessEqual(r["failed_count"], 1)

    def test_poor_page_many_failures(self):
        doc = htmldoc.from_file(_path.fixture("poor_page.html"))
        r = diagnose.diagnose(doc)
        self.assertGreaterEqual(r["failed_count"], 3)
        self.assertEqual(r["verdict"], "可被引用障碍较多")

    def test_seven_root_causes_present(self):
        doc = htmldoc.from_file(_path.fixture("poor_page.html"))
        r = diagnose.diagnose(doc, market="global")
        causes = [f["cause"] for f in r["findings"]]
        self.assertTrue(any("canonical" in c for c in causes))
        self.assertTrue(any("FAQPage" in c for c in causes))
        self.assertTrue(any("信息缺口" in c for c in causes))

    def test_icp_flag_for_cn(self):
        doc = htmldoc.from_string("<html><body><h1>x</h1></body></html>")
        r = diagnose.diagnose(doc, market="cn")
        self.assertTrue(any("ICP" in f["cause"] for f in r["findings"]))

    def test_icp_pass_when_beian_present(self):
        doc = htmldoc.from_string(
            "<html><body><footer>京ICP备12345678号</footer></body></html>")
        r = diagnose.diagnose(doc, market="cn")
        icp = next(f for f in r["findings"] if "ICP" in f["cause"])
        self.assertEqual(icp["status"], "pass")


if __name__ == "__main__":
    unittest.main()
