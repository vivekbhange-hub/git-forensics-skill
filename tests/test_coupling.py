"""Tests for skills/gitfx-coupling/coupling.py (pair counts, confidence, flags, bulk skipping, CLI)."""
import json
import unittest

from _gitrepo import GitRepo, demo_repo, lines, make_repo, needs_git, scratch_dir
from _load import TempDir, load, run_main

cp = load("gitfx-coupling", "coupling")


class HelperTests(unittest.TestCase):
    def test_is_test_path(self):
        for path in ("tests/test_a.py", "src/a_test.go", "web/a.spec.ts", "src/__tests__/a.js", "spec/a_spec.rb"):
            with self.subTest(path=path):
                self.assertTrue(cp.is_test_path(path))
        for path in ("src/alpha.py", "src/contest.py", "docs/testing.md"):
            with self.subTest(path=path):
                self.assertFalse(cp.is_test_path(path))

    def test_stem_of(self):
        self.assertEqual(cp.stem_of("a/b/orders.py"), "orders")
        self.assertEqual(cp.stem_of("a/archive.tar.gz"), "archive")
        self.assertEqual(cp.stem_of(".gitignore"), ".gitignore")

    def test_is_test_pair(self):
        self.assertTrue(cp.is_test_pair("src/orders.py", "tests/test_orders.py", False))
        self.assertTrue(cp.is_test_pair("src/x.py", "tests/test_orders.py", True))
        self.assertFalse(cp.is_test_pair("src/invoice.py", "tests/test_orders.py", False))
        self.assertFalse(cp.is_test_pair("src/alpha.py", "src/beta.py", True))

    def test_counter_counts_pairs_both_ways_once(self):
        counter = cp.Counter(2, 1000)
        counter.add({"a", "b", "c"})
        counter.add({"b", "a"})
        self.assertEqual(counter.pairs[("a", "b")], 2)
        self.assertEqual(counter.pairs[("a", "c")], 1)
        self.assertEqual(counter.files, {"a": 2, "b": 2, "c": 1})

    def test_counter_prunes_rare_pairs(self):
        counter = cp.Counter(2, 3)
        counter.add({"a", "b"})
        counter.add({"a", "b"})
        counter.add({"c", "d", "e"})
        self.assertTrue(counter.pruned)
        self.assertEqual(list(counter.pairs), [("a", "b")])

    def test_clusters(self):
        rows = [{"a": "a", "b": "b"}, {"a": "b", "b": "c"}, {"a": "x", "b": "y"}]
        self.assertEqual(cp.clusters(rows), [["a", "b", "c"], ["x", "y"]])


@needs_git
class SmallRepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def v(n):
            return lines(3, prefix="v%d_" % n)
        commits = [("ava", "2026-01-01", "Init", {"src/alpha.py": "a\n", "src/beta.py": "b\n", "docs/alpha.md": "d\n",
                                                    "yarn.lock": "x\n", "solo.py": "s\n"})]
        for n in range(2, 7):       # a and b change together five more times, docs/alpha.md three times
            files = {"src/alpha.py": v(n), "src/beta.py": v(n), "yarn.lock": v(n)}
            if n % 2 == 0:
                files["docs/alpha.md"] = v(n)
            commits.append(("ben", "2026-02-%02d" % n, "Change %d" % n, files))
        commits.append(("ben", "2026-03-01", "Solo", {"solo.py": "t\n"}))
        bulk = dict(("bulk/f%02d.py" % i, "x\n") for i in range(12))
        bulk["src/alpha.py"] = "bulk\n"
        bulk["src/beta.py"] = "bulk\n"
        commits.append(("chen", "2026-03-05", "Bulk reformat", bulk))
        cls.repo = make_repo(commits)

    def report(self, *extra):
        code, out, err = run_main(cp, [self.repo, "--json", "--min-shared", "2"] + list(extra))
        self.assertEqual((code, err), (0, ""))
        return json.loads(out)

    def pair(self, data, a, b):
        for row in data["pairs"]:
            if (row["a"], row["b"]) == (a, b):
                return row
        self.fail("pair %s %s missing from %s" % (a, b, [(r["a"], r["b"]) for r in data["pairs"]]))

    def test_shared_support_and_confidence(self):
        data = self.report("--max-files", "10")
        row = self.pair(data, "src/alpha.py", "src/beta.py")
        self.assertEqual(row["shared"], 6)      # init plus five changes; the bulk commit is skipped
        self.assertEqual((row["commits_a"], row["commits_b"]), (6, 6))
        self.assertEqual((row["confidence_a_to_b"], row["confidence_b_to_a"]), (1.0, 1.0))
        self.assertEqual(data["skipped_bulk_commits"], 1)

    def test_confidence_is_directional(self):
        data = self.report("--max-files", "10", "--min-confidence", "0.5")
        row = self.pair(data, "docs/alpha.md", "src/alpha.py")
        self.assertEqual(row["shared"], 3 + 1)      # three even changes plus the initial commit
        self.assertEqual(row["confidence_a_to_b"], 1.0)
        self.assertEqual(row["confidence_b_to_a"], round(4 / 6.0, 2))

    def test_without_the_cap_bulk_commit_counts(self):
        data = self.report("--max-files", "100")
        self.assertEqual(self.pair(data, "src/alpha.py", "src/beta.py")["shared"], 7)

    def test_cross_module_and_reference_flags(self):
        data = self.report("--max-files", "10")
        same = self.pair(data, "src/alpha.py", "src/beta.py")
        self.assertFalse(same["cross_module"])
        cross = self.pair(data, "docs/alpha.md", "src/alpha.py")
        self.assertTrue(cross["cross_module"])
        self.assertIs(cross["linked"], False)      # neither file mentions the other's name
        self.assertTrue(cross["hidden"])

    def test_excluded_files_never_appear(self):
        data = self.report("--max-files", "10")
        for row in data["pairs"]:
            self.assertNotIn("yarn.lock", (row["a"], row["b"]))

    def test_min_shared_and_min_confidence_filter(self):
        self.assertEqual(self.report("--max-files", "10", "--min-shared", "7")["pairs"], [])
        data = self.report("--max-files", "10", "--min-confidence", "1.0")
        for row in data["pairs"]:
            self.assertEqual(max(row["confidence_a_to_b"], row["confidence_b_to_a"]), 1.0)

    def test_hidden_only(self):
        data = self.report("--max-files", "10", "--hidden-only")
        self.assertTrue(data["pairs"])
        self.assertTrue(all(r["hidden"] for r in data["pairs"]))

    def test_clusters_in_report(self):
        data = self.report("--max-files", "10")
        self.assertEqual(data["clusters"], [["docs/alpha.md", "src/alpha.py", "src/beta.py"]])

    def test_top(self):
        self.assertEqual(len(self.report("--max-files", "10", "--top", "1")["pairs"]), 1)

    def test_markdown(self):
        code, out, _ = run_main(cp, [self.repo, "--max-files", "10", "--min-shared", "2", "--label", "proj"])
        self.assertTrue(out.startswith("# Temporal coupling: proj\n"))
        self.assertIn("| 1 | `src/alpha.py` | `src/beta.py` | 6 |", out)
        self.assertIn("hidden dependency?", out)
        self.assertNotIn("\r", out)

    def test_fail_above(self):
        args = [self.repo, "--max-files", "10", "--min-shared", "2", "--fail-above"]
        self.assertEqual(run_main(cp, args + ["1"])[0], 1)
        self.assertEqual(run_main(cp, args + ["50"])[0], 0)

    def test_window_limits_commits(self):
        data = self.report("--max-files", "10", "--since", "2026-02-05 00:00:00 +0000", "--until", "2026-02-28 00:00:00 +0000")
        self.assertEqual(self.pair(data, "src/alpha.py", "src/beta.py")["shared"], 2)

    def test_output_is_deterministic(self):
        args = [self.repo, "--json", "--max-files", "10", "--min-shared", "2"]
        self.assertEqual(run_main(cp, args)[1], run_main(cp, args)[1])


@needs_git
class ReferenceAndRenameTests(unittest.TestCase):
    def test_a_mentioned_name_clears_the_hidden_flag(self):
        commits = [("ava", "2026-01-01", "Init", {"api/server.py": "x = 1\n", "core/engine.py": "x = 1\n"})]
        for n in range(2, 6):
            commits.append(("ben", "2026-01-%02d" % n, "Change", {
                "api/server.py": "import engine\nx = %d\n" % n, "core/engine.py": "x = %d\n" % n}))
        repo = make_repo(commits)
        code, out, _ = run_main(cp, [repo, "--json"])
        row = json.loads(out)["pairs"][0]
        self.assertIs(row["linked"], True)
        self.assertFalse(row["hidden"])

    def test_renamed_file_keeps_its_history(self):
        commits = [("ava", "2026-01-01", "Init", {"a.py": "1\n", "old.py": "1\n"})]
        commits.append(("ava", "2026-01-02", "Both", {"a.py": "2\n", "old.py": "2\n"}))
        commits.append(("ava", "2026-01-03", "Rename", {"new.py": ("mv", "old.py")}))
        commits.append(("ava", "2026-01-04", "Both again", {"a.py": "3\n", "new.py": "3\n"}))
        repo = make_repo(commits)
        code, out, _ = run_main(cp, [repo, "--json", "--min-shared", "3"])
        pairs = json.loads(out)["pairs"]
        self.assertEqual([(p["a"], p["b"], p["shared"]) for p in pairs], [("a.py", "new.py", 3)])

    def test_odd_names(self):
        commits = [("ava", "2026-01-01", "Init", {"a b.py": "1\n", "café.py": "1\n"})]
        for n in range(2, 5):
            commits.append(("ava", "2026-01-%02d" % n, "Both", {"a b.py": "%d\n" % n, "café.py": "%d\n" % n}))
        code, out, _ = run_main(cp, [make_repo(commits), "--json"])
        self.assertEqual([(p["a"], p["b"]) for p in json.loads(out)["pairs"]], [("a b.py", "café.py")])


@needs_git
class DemoTests(unittest.TestCase):
    def test_demo_finds_the_hidden_billing_dependency(self):
        code, out, _ = run_main(cp, [demo_repo(), "--json", "--min-shared", "4", "--min-confidence", "0.6"])
        data = json.loads(out)
        pairs = dict(((p["a"], p["b"]), p) for p in data["pairs"])
        hidden = pairs[("billing/invoice.py", "src/shop/orders.py")]
        self.assertEqual(hidden["shared"], 12)
        self.assertTrue(hidden["hidden"])
        self.assertTrue(pairs[("src/shop/orders.py", "tests/test_orders.py")]["test_pair"])
        self.assertFalse(pairs[("src/shop/orders.py", "src/shop/pricing.py")]["cross_module"])
        self.assertEqual(data["skipped_bulk_commits"], 2)

    def test_demo_bulk_adapters_do_not_couple(self):
        code, out, _ = run_main(cp, [demo_repo(), "--json", "--min-shared", "1", "--min-confidence", "0", "--top", "500"])
        for row in json.loads(out)["pairs"]:
            self.assertNotIn("adapters", row["a"])


class ErrorTests(unittest.TestCase):
    def test_not_a_repository(self):
        with TempDir() as tmp:
            code, out, err = run_main(cp, [tmp])
        self.assertEqual(code, 2)
        self.assertIn("coupling:", err)

    def test_bad_numbers(self):
        self.assertEqual(run_main(cp, [".", "--min-confidence", "2"])[0], 2)
        self.assertEqual(run_main(cp, [".", "--max-files", "0"])[0], 2)
        self.assertEqual(run_main(cp, [".", "--top", "0"])[0], 2)

    @needs_git
    def test_empty_repository(self):
        path = scratch_dir()
        GitRepo(path)
        self.assertEqual(run_main(cp, [path])[0], 2)


if __name__ == "__main__":
    unittest.main()
