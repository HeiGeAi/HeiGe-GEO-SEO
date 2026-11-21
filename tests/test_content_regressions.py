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
        score_res = self.run_cli('score', '--input', 'tests/fixtures/good_page.html')
        self.assertEqual(score_res.returncode, 0, score_res.stderr)
        self.assertIn('总分:', score_res.stdout)

        llms_res = self.run_cli('llms', '--site', 'Example', '--summary', 'Example docs',
                                '--links', 'tests/fixtures/quickstart-links.txt')
        self.assertEqual(llms_res.returncode, 0, llms_res.stderr)
        self.assertIn('- [Documentation](https://example.com/docs): Example documentation', llms_res.stdout)
        self.assertIn('- [About](https://example.com/about): Example project overview', llms_res.stdout)
        self.assertIn('- [FAQ](https://example.com/faq)\n', llms_res.stdout)

    def test_not_a_directory_and_bad_output_paths_have_no_tracebacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            file_path = root / 'page.html'
            file_path.write_text('<html><body>hi</body></html>')
            not_a_dir = file_path / 'child.html'

            r = self.run_cli('score', '--input', not_a_dir)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertEqual(r.stdout, '')
            self.assertIn(str(not_a_dir), r.stderr)
            self.assertNotIn('Traceback', r.stderr)

            for bad_out in [root, root / 'missing_dir' / 'out.txt']:
                r = self.run_cli('robots', '--out', bad_out)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertEqual(r.stdout, '')
                self.assertIn(str(bad_out), r.stderr)
                self.assertNotIn('Traceback', r.stderr)

    def test_faq_cli_qa_rejects_empty_question_or_answer(self):
        for bad in ['::answer', 'question::   ']:
            r = self.run_cli('schema', '--type', 'faqpage', '--qa', bad)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertEqual(r.stdout, '')
            self.assertIn('问题和答案不能为空', r.stderr)
            self.assertNotIn('Traceback', r.stderr)

    def test_measure_requires_brand_and_json_shape_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            records = root / 'records.json'
            records.write_text('[{"prompt":"p","engine":"豆包","answer":"foo"}]')
            bad_shape = root / 'bad.json'
            bad_shape.write_text('"not-a-list"')

            r = self.run_cli('measure', '--input', records)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertEqual(r.stdout, '')
            self.assertIn('--brand', r.stderr)

            for args in [
                ('sov', '--input', bad_shape, '--brand', 'Foo'),
                ('lostprompt', '--input', bad_shape, '--brand', 'Foo'),
                ('factcheck', '--input', records, '--brand', 'Foo', '--facts', bad_shape),
                ('measure', '--input', bad_shape, '--brand', 'Foo'),
                ('cwv', '--psi', bad_shape),
            ]:
                res = self.run_cli(*args)
                self.assertEqual(res.returncode, 2, f"{args}: {res.stderr}")
                self.assertEqual(res.stdout, '')
                self.assertNotIn('Traceback', res.stderr)

    def test_local_site_root_alias_matches_resolved_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = pathlib.Path(tmp)
            root = parent / 'site'
            root.mkdir()
            alias = parent / 'site-alias'
            try:
                alias.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(str(error))
            (root / 'index.html').write_text('<a href="/about.html">About</a>')
            (root / 'about.html').write_text('<a href="/index.html">Home</a>')
            for files in [('index.html', 'about.html'),
                          (str(alias / 'index.html'), str(root / 'about.html'))]:
                result = self.run_cli('internal-links', *files, '--root', alias, cwd=alias)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertEqual(json.loads(result.stdout)['orphan_count'], 0)
            outside = parent / 'outside.html'
            outside.write_text('outside')
            result = self.run_cli('internal-links', outside, '--root', alias, cwd=alias)
            self.assertEqual(result.returncode, 2)
            self.assertIn('文件不在站点根目录内', result.stderr)


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
