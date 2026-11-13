"""The bundled demo: committed outputs must be exactly what the scripts produce from the synthetic history."""
import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from _gitrepo import demo_repo, needs_git, regen, remove_tree
from _load import ROOT

OUTPUT = ROOT / "examples" / "output"
EXPECTED = ["coupling-hidden.md", "coupling.md", "hotspots.json", "hotspots.md", "owners-fast.md", "owners.md"]


class CommittedOutputTests(unittest.TestCase):
    def test_expected_files_are_committed(self):
        self.assertEqual(sorted(p.name for p in OUTPUT.iterdir()), EXPECTED)

    def test_outputs_use_lf_and_utf8_and_no_local_paths(self):
        for name in EXPECTED:
            with self.subTest(file=name):
                data = (OUTPUT / name).read_bytes()
                self.assertNotIn(b"\r", data)
                text = data.decode("utf-8")
                self.assertNotRegex(text, r"[A-Za-z]:\\|/tmp/|/Users/|/home/|gitfx-test-")

    def test_gitignore_covers_the_demo_repository(self):
        self.assertIn("examples/demo-repo/", (ROOT / ".gitignore").read_text(encoding="utf-8").split())

    def test_compare_reports_differences(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            (Path(a) / "x.txt").write_text("1", encoding="utf-8")
            (Path(b) / "x.txt").write_text("2", encoding="utf-8")
            (Path(b) / "y.txt").write_text("2", encoding="utf-8")
            self.assertEqual(regen.compare(Path(a), Path(b)), ["y.txt: not committed", "x.txt: content differs"])


@needs_git
class DeterminismTests(unittest.TestCase):
    def test_regenerating_is_byte_identical_from_any_working_directory(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                out = Path(tmp) / "out"
                self.assertEqual(regen.generate(out), EXPECTED)
                self.assertEqual(regen.compare(OUTPUT, out), [])
            finally:
                os.chdir(previous)

    def test_check_mode(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(regen.main(["--check"]), 0)
        self.assertIn("up to date", out.getvalue())

    def test_a_failing_script_is_reported(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
            regen.render("gitfx-hotspots", "hotspots", [str(ROOT / "no-such-folder")])

    def test_build_demo_refuses_a_non_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "keep.txt").write_text("x", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(regen.main(["--build-demo", tmp]), 2)

    def test_build_demo_builds_a_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mine"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(regen.main(["--build-demo", str(target)]), 0)
            self.assertTrue((target / ".git").is_dir())
            self.assertTrue((target / "src" / "shop" / "orders.py").is_file())
            remove_tree(str(target))


@needs_git
class SyntheticHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(demo_repo())

    def git(self, *args):
        import subprocess
        proc = subprocess.run(["git", "-C", str(self.repo)] + list(args), stdout=subprocess.PIPE,
                              env=dict(os.environ, LC_ALL="C"))
        return proc.stdout.decode("utf-8").splitlines()

    def test_history_is_fully_synthetic(self):
        rows = self.git("log", "--format=%an|%ae|%cn|%ce")
        self.assertEqual(len(rows), 51)
        for row in rows:
            for field in row.split("|")[1::2]:
                self.assertRegex(field, r"@([a-z]+\.)?example\.(com|net)$")

    def test_dates_are_fixed(self):
        dates = self.git("log", "--format=%ad|%cd", "--date=iso-strict")
        self.assertTrue(all(d.split("|")[0] == d.split("|")[1] for d in dates))
        self.assertEqual(dates[-1].split("|")[0], "2026-01-05T10:00:00+00:00")
        self.assertTrue(all(re.match(r"2026-\d\d-\d\dT1[02]:00:00\+00:00", d) for d in [x.split("|")[0] for x in dates]))

    def test_history_has_the_scenarios_the_readme_describes(self):
        subjects = self.git("log", "--format=%s")
        self.assertIn("Rename util to helpers", subjects)
        self.assertIn("style: reformat adapters", subjects)
        self.assertIn("Vendor lib.js 2.1", subjects)
        self.assertEqual(sum(1 for s in subjects if s.startswith("chore(deps)")), 5)
        self.assertTrue(any("old.example.net" in line for line in self.git("log", "--format=%ae")))

    def test_two_builds_have_identical_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "again"
            regen.build_demo(other)
            import subprocess
            head = subprocess.run(["git", "-C", str(other), "rev-parse", "HEAD"], stdout=subprocess.PIPE)
            self.assertEqual(head.stdout.decode().strip(), self.git("rev-parse", "HEAD")[0])
            remove_tree(str(other))


class DemoContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hot = (OUTPUT / "hotspots.md").read_text(encoding="utf-8")
        cls.coupling = (OUTPUT / "coupling.md").read_text(encoding="utf-8")
        cls.hidden = (OUTPUT / "coupling-hidden.md").read_text(encoding="utf-8")
        cls.owners = (OUTPUT / "owners.md").read_text(encoding="utf-8")
        cls.fast = (OUTPUT / "owners-fast.md").read_text(encoding="utf-8")

    def test_hotspots(self):
        self.assertIn("| 1 | `src/shop/orders.py` | 100.0 | 19 |", self.hot)
        self.assertNotIn("package-lock.json", self.hot)
        self.assertNotIn("vendor/lib.js", self.hot)
        self.assertIn("src/shop/helpers.py", self.hot)

    def test_coupling(self):
        self.assertIn("skipped 2 bulk commits touching more than 30 files", self.coupling)
        self.assertRegex(self.coupling, r"`billing/invoice.py` \| `src/shop/orders.py` \| 12 \|")
        self.assertIn("test and code", self.coupling)
        self.assertIn("## Clusters", self.coupling)

    def test_hidden_only(self):
        for line in self.hidden.splitlines():
            if line.startswith("| ") and "`" in line:
                self.assertIn("hidden dependency?", line)

    def test_owners(self):
        self.assertIn("| `src/shop/legacy_sync.py` | Eli Former | 99.2% | 2026-03-10 | 236 |", self.owners)
        self.assertIn("5 bot commits excluded", self.owners)
        self.assertIn("| commits |", self.fast)
        self.assertNotIn("| blame |", self.fast)

    def test_json_example_parses(self):
        import json
        data = json.loads((OUTPUT / "hotspots.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["hotspots"]), 3)
        self.assertEqual(data["hotspots"][0]["file"], "src/shop/orders.py")


if __name__ == "__main__":
    unittest.main()
