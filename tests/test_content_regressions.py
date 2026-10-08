import json
import re
import shlex
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/geo_cli.py"

class ContentRegressions(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(CLI), *map(str,args)], cwd=cwd or ROOT, text=True, capture_output=True)

    def test_faq_file_is_atomic_and_line_numbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = pathlib.Path(tmp)/'qa.txt'
            for text, status in [('q::a\n\nq2::a::more',0),('q::a\nbad row',2),('q::a\n::empty',2)]:
                f.write_text(text)
                r=self.run_cli('schema','--type','faqpage','--qa-file',f)
                self.assertEqual(r.returncode,status,r.stderr)
                if status:
                    self.assertEqual(r.stdout,'')
                    self.assertIn(str(f)+':2:',r.stderr)
                else:
                    self.assertIn('a::more',r.stdout)

    def test_bad_files_have_no_tracebacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            for f in [pathlib.Path(tmp)/'missing',pathlib.Path(tmp)]:
                for args in [('score','--input',f),('llms','--site','Example','--summary','Example docs','--links',f)]:
                    r=self.run_cli(*args)
                    self.assertEqual(r.returncode,2,r.stderr)
                    self.assertEqual(r.stdout,'')
                    self.assertIn(str(f),r.stderr)
                    self.assertNotIn('Traceback',r.stderr)

    def test_local_site_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            (root/'docs').mkdir()
            (root/'index.html').write_text('<a href="about.html">About</a><a href="/docs/index.html">Docs</a>')
            (root/'about.html').write_text('<a href="index.html">Home</a>')
            (root/'docs/index.html').write_text('<a href="../about.html">About</a><a href="https://example.com/index.html">Home</a>')
            for files in [('index.html','about.html','docs/index.html'),tuple(str(root/p) for p in ('index.html','about.html','docs/index.html'))]:
                r=self.run_cli('internal-links',*files,'--root',root,'--home','index.html','--host','example.com',cwd=root)
                self.assertEqual(r.returncode,0,r.stderr+r.stdout)
                data=json.loads(r.stdout)
                self.assertEqual(data['orphan_count'],0)
                self.assertEqual(data['inbound_by_page']['/about.html'],2)
                self.assertEqual(data['inbound_by_page']['/index.html'],2)

    def test_quickstart_inputs(self):
        for args in [('score','--input','tests/fixtures/good_page.html'),
                     ('llms','--site','Example','--summary','Example docs','--links','tests/fixtures/quickstart-links.txt')]:
            r=self.run_cli(*args)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(r.stdout)


    def test_readme_quickstart_commands_verbatim(self):
        readme = (ROOT / "README.md").read_text()
        sections = [readme.split("## 快速开始",1)[1].split("\n## ",1)[0],
                    readme.split("### Quick start",1)[1].split("\n### ",1)[0]]
        count = 0
        for section in sections:
            for command in re.findall(r"^python3 scripts/geo_cli.py .+$", section, re.M):
                result = self.run_cli(*shlex.split(command)[2:])
                self.assertEqual(result.returncode, 0, command + result.stderr)
                self.assertTrue(result.stdout)
                count += 1
        self.assertEqual(count, 9)
