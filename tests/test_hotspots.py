"""Tests for skills/gitfx-hotspots/hotspots.py (scoring, excludes, renames, windows, CLI)."""
import json
import unittest

from _gitrepo import GitRepo, demo_repo, lines, make_repo, needs_git, scratch_dir
from _load import TempDir, load, run_main

hs = load("gitfx-hotspots", "hotspots")


class PureFunctionTests(unittest.TestCase):
    def test_measure_counts_lines_and_indentation(self):
        count, max_indent, mean_indent = hs.measure(b"a\n    b\n\n        c\n")
        self.assertEqual(count, 4)
        self.assertEqual(max_indent, 2.0)
        self.assertEqual(mean_indent, 1.0)

    def test_measure_tabs_count_as_four_columns(self):
        self.assertEqual(hs.measure(b"\tx\n")[1], 1.0)

    def test_measure_empty_and_blank_files(self):
        self.assertEqual(hs.measure(b""), (0, 0.0, 0.0))
        self.assertEqual(hs.measure(b"\n\n")[1:], (0.0, 0.0))

    def test_percentile_ranks_share_ties(self):
        self.assertEqual(hs.percentile_ranks([5, 5, 9]), [0.5, 0.5, 1.0])
        self.assertEqual(hs.percentile_ranks([1]), [1.0])
        self.assertEqual(hs.percentile_ranks([]), [])

    def test_fix_regex(self):
        for subject in ("Fix crash", "hotfix: x", "Revert the add", "regression in cart", "bugfix", "fixes #12"):
            with self.subTest(subject=subject):
                self.assertTrue(hs.FIX_RE.search(subject))
        for subject in ("Add prefix handling", "fixture cleanup", "Add feature", "debug logging"):
            with self.subTest(subject=subject):
                self.assertIsNone(hs.FIX_RE.search(subject))

    def test_default_excludes(self):
        patterns = hs.exclude_patterns([])
        for path in ("package-lock.json", "a/b/yarn.lock", "vendor/x.js", "src/node_modules/y/z.js",
                     "static/app.min.js", "img/logo.png", "api/x.pb.go", "dist/out.js", "Cargo.lock"):
            with self.subTest(path=path):
                self.assertTrue(hs.is_excluded(path, patterns))
        for path in ("src/app.py", "vendors.py", "docs/vendor-notes.md", "src/builder.py"):
            with self.subTest(path=path):
                self.assertFalse(hs.is_excluded(path, patterns))

    def test_user_excludes_and_no_defaults(self):
        self.assertTrue(hs.is_excluded("db/x.sql", hs.exclude_patterns(["*.sql"])))
        self.assertFalse(hs.is_excluded("vendor/x.js", hs.exclude_patterns([], use_defaults=False)))
        self.assertTrue(hs.is_excluded("legacy/a/b.py", ["legacy/"]))

    def test_top_dir(self):
        self.assertEqual(hs.top_dir("a/b/c.py"), "a")
        self.assertEqual(hs.top_dir("c.py"), ".")


@needs_git
class SmallRepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        big = lines(40, "        ")
        cls.repo = make_repo([
            ("ava", "2026-01-05", "Initial", {"big.py": big, "small.py": "a = 1\n", "lone.py": big,
                                              "package-lock.json": "{}\n", "logo.png": b"\x89PNG\0\0data",
                                              "bin.dat": b"\0\1\2\3"}),
            ("ben", "2026-02-01", "Fix bug in big", {"big.py": big + "        extra = 1\n"}),
            ("ben", "2026-03-01", "More work", {"big.py": big + "        extra = 2\n", "small.py": "a = 2\n",
                                               "package-lock.json": "{ }\n"}),
            ("chen", "2026-04-01", "Another fix", {"big.py": big + "        extra = 3\n"}),
            ("chen", "2026-05-01", "Drop lone", {"lone.py": None}),
            ("chen", "2026-05-02", "Add notes", {"notes with spaces.md": "hello\n", "café.txt": "x\n"}),
        ])

    def report(self, *extra):
        code, out, err = run_main(hs, [self.repo, "--json", "--top", "50"] + list(extra))
        self.assertEqual((code, err), (0, ""))
        return json.loads(out)

    def files(self, data):
        return [row["file"] for row in data["hotspots"]]

    def test_big_churned_file_ranks_first(self):
        data = self.report()
        row = data["hotspots"][0]
        self.assertEqual(row["file"], "big.py")
        self.assertEqual((row["commits"], row["authors"], row["fix_commits"]), (4, 3, 2))
        self.assertEqual(row["fix_share"], 50.0)
        self.assertEqual(row["score"], 100.0)

    def test_deleted_binary_and_lockfile_are_not_listed(self):
        names = self.files(self.report())
        for gone in ("lone.py", "package-lock.json", "logo.png", "bin.dat"):
            self.assertNotIn(gone, names)

    def test_no_default_excludes_brings_lockfile_back(self):
        self.assertIn("package-lock.json", self.files(self.report("--no-default-excludes")))

    def test_binary_content_is_skipped_even_when_not_excluded_by_name(self):
        self.assertNotIn("bin.dat", self.files(self.report("--no-default-excludes")))

    def test_odd_file_names_survive(self):
        names = self.files(self.report())
        self.assertIn("notes with spaces.md", names)
        self.assertIn("café.txt", names)

    def test_window(self):
        data = self.report("--since", "2026-03-15")
        self.assertEqual(self.files(data)[0], "big.py")
        self.assertEqual(data["hotspots"][0]["commits"], 1)
        data = self.report("--until", "2026-01-31")
        self.assertEqual(data["commits_scanned"], 1)

    def test_path_filter(self):
        self.assertEqual(self.files(self.report("--path", "small.py")), ["small.py"])

    def test_exclude_glob(self):
        self.assertNotIn("small.py", self.files(self.report("--exclude", "small.*")))

    def test_min_commits(self):
        self.assertEqual(self.files(self.report("--min-commits", "2")), ["big.py", "small.py"])

    def test_top_limits_rows(self):
        code, out, _ = run_main(hs, [self.repo, "--json", "--top", "2"])
        self.assertEqual(len(json.loads(out)["hotspots"]), 2)

    def test_markdown_report(self):
        code, out, _ = run_main(hs, [self.repo, "--label", "proj"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("# Hotspots: proj\n"))
        self.assertIn("| 1 | `big.py` | 100.0 | 4 |", out)
        self.assertNotIn("\r", out)

    def test_output_file_uses_lf(self):
        with TempDir() as tmp:
            target = tmp + "/out.md"
            self.assertEqual(run_main(hs, [self.repo, "-o", target])[0], 0)
            with open(target, "rb") as handle:
                data = handle.read()
            self.assertNotIn(b"\r", data)
            self.assertTrue(data.startswith(b"# Hotspots:"))

    def test_fail_above(self):
        self.assertEqual(run_main(hs, [self.repo, "--fail-above", "99"])[0], 1)
        self.assertEqual(run_main(hs, [self.repo, "--fail-above", "101"])[0], 0)

    def test_output_is_deterministic(self):
        self.assertEqual(run_main(hs, [self.repo, "--json"])[1], run_main(hs, [self.repo, "--json"])[1])


@needs_git
class RenameAndMergeTests(unittest.TestCase):
    def test_history_follows_a_rename(self):
        body = lines(20)
        repo = make_repo([
            ("ava", "2026-01-01", "Add old", {"old.py": body}),
            ("ben", "2026-01-02", "Edit old", {"old.py": body + "y = 1\n"}),
            ("ben", "2026-01-03", "Rename", {"new.py": ("mv", "old.py")}),
            ("chen", "2026-01-04", "Edit new", {"new.py": body + "y = 2\n"}),
        ])
        code, out, _ = run_main(hs, [repo, "--json"])
        rows = json.loads(out)["hotspots"]
        self.assertEqual([r["file"] for r in rows], ["new.py"])
        self.assertEqual(rows[0]["commits"], 3)      # add, edit, later edit; the pure rename is not churn
        self.assertEqual(rows[0]["authors"], 3)

    def test_merge_commits_are_skipped(self):
        repo = make_repo([("ava", "2026-01-01", "Init", {"a.py": lines(5)})])
        g = GitRepo(repo)
        g.git("checkout", "-q", "-b", "feature")
        g.write("b.py", lines(5))
        g.commit("Add b", "ben", "2026-01-02T10:00:00+0000")
        g.git("checkout", "-q", "main")
        g.write("a.py", lines(6))
        g.commit("Edit a", "ava", "2026-01-03T10:00:00+0000")
        g.git("merge", "--no-ff", "-q", "-m", "Merge feature", "feature", who="ava", when="2026-01-04T10:00:00+0000")
        code, out, _ = run_main(hs, [repo, "--json"])
        self.assertEqual(json.loads(out)["commits_scanned"], 3)


@needs_git
class DemoTests(unittest.TestCase):
    def test_demo_orders_is_the_top_hotspot(self):
        code, out, _ = run_main(hs, [demo_repo(), "--json", "--top", "5"])
        data = json.loads(out)
        top = data["hotspots"][0]
        self.assertEqual((top["file"], top["commits"], top["authors"]), ("src/shop/orders.py", 19, 4))
        self.assertGreater(top["fix_share"], 50)
        self.assertEqual(data["repo"], "demo-repo")

    def test_demo_skips_lockfile_and_vendor_and_follows_rename(self):
        code, out, _ = run_main(hs, [demo_repo(), "--json", "--top", "100"])
        rows = json.loads(out)["hotspots"]
        names = [r["file"] for r in rows]
        self.assertNotIn("package-lock.json", names)
        self.assertNotIn("vendor/lib.js", names)
        self.assertNotIn("src/shop/util.py", names)
        helpers = [r for r in rows if r["file"] == "src/shop/helpers.py"][0]
        self.assertEqual(helpers["commits"], 4)


class ErrorTests(unittest.TestCase):
    def test_not_a_repository(self):
        with TempDir() as tmp:
            code, out, err = run_main(hs, [tmp])
        self.assertEqual(code, 2)
        self.assertIn("hotspots:", err)

    def test_missing_directory(self):
        self.assertEqual(run_main(hs, ["/no/such/dir-gitfx"])[0], 2)

    def test_bad_top(self):
        self.assertEqual(run_main(hs, [".", "--top", "0"])[0], 2)

    def test_unknown_flag_is_a_usage_error(self):
        self.assertEqual(run_main(hs, ["--bogus"])[0], 2)

    @needs_git
    def test_repository_without_commits(self):
        path = scratch_dir()
        GitRepo(path)
        code, out, err = run_main(hs, [path])
        self.assertEqual(code, 2)
        self.assertIn("no commits", err)


if __name__ == "__main__":
    unittest.main()
