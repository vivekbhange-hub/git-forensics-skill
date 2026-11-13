"""Tests for skills/gitfx-owners/owners.py (bus factor, aliases, bots, blame, knowledge at risk, CLI)."""
import json
import re
import unittest

from _gitrepo import GitRepo, demo_repo, lines, make_repo, needs_git, scratch_dir
from _load import TempDir, load, run_main

ow = load("gitfx-owners", "owners")


def people(domains=(), bots=True):
    res = [re.compile(p, re.IGNORECASE) for p in ow.BOT_PATTERNS] if bots else []
    return ow.People(domains, res)


class PureTests(unittest.TestCase):
    def test_bus_factor(self):
        self.assertEqual(ow.bus_factor({}), 0)
        self.assertEqual(ow.bus_factor({"a": 10}), 1)
        self.assertEqual(ow.bus_factor({"a": 50, "b": 30, "c": 20}), 1)
        self.assertEqual(ow.bus_factor({"a": 40, "b": 30, "c": 30}), 2)
        self.assertEqual(ow.bus_factor({"a": 1, "b": 1, "c": 1, "d": 1}), 2)
        self.assertEqual(ow.bus_factor({"a": 1, "b": 1, "c": 1}), 2)

    def test_top_owner_breaks_ties_by_key(self):
        self.assertEqual(ow.top_owner({"b": 5, "a": 5}), ("a", 0.5))
        self.assertEqual(ow.top_owner({}), (None, 0.0))

    def test_identity_merging_by_domain(self):
        p = people(["corp.example.com", "users.noreply.example.com"])
        self.assertEqual(p.key("Ava", "ava@corp.example.com"), "ava")
        self.assertEqual(p.key("Ava E", "12345+ava@users.noreply.example.com"), "ava")
        self.assertEqual(p.key("Ava", "AVA@Corp.Example.com"), "ava")
        self.assertEqual(p.key("Ava", "ava@other.example.org"), "ava@other.example.org")
        self.assertEqual(p.display("ava"), "Ava")

    def test_identity_without_email(self):
        self.assertEqual(people().key("Pat Q", ""), "name:pat q")

    def test_display_uses_the_commonest_name(self):
        p = people()
        p.key("Ava", "a@x.example.com")
        p.key("A. Example", "a@x.example.com")
        p.key("A. Example", "a@x.example.com")
        self.assertEqual(p.display("a@x.example.com"), "A. Example")

    def test_bot_detection(self):
        p = people()
        for name, email in (("dependabot[bot]", "x@example.com"), ("renovate-bot", "r@example.com"),
                            ("CI", "ci-bot@example.com"), ("github-actions", "g@example.com")):
            with self.subTest(name=name):
                self.assertTrue(p.is_bot(name, email))
        self.assertFalse(p.is_bot("Robert Bottom", "rob@example.com"))
        self.assertFalse(people(bots=False).is_bot("dependabot[bot]", "x@example.com"))

    def test_parse_day(self):
        self.assertIsNotNone(ow.parse_day("2026-11-01"))
        self.assertIsNone(ow.parse_day("11/01/2026"))


@needs_git
class SmallRepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        main_text = lines(10, prefix="m")
        ben_lines = lines(4, prefix="b")
        cls.repo = make_repo([
            ("ava", "2026-01-01", "Init", {"core.py": main_text, "shared.py": lines(4, prefix="s"),
                                           ".mailmap": "Ava Example <ava@example.com> <ava.e@old.example.net>\n"}),
            ("ava_old", "2026-01-05", "Old mail", {"core.py": main_text + lines(2, prefix="o")}),
            ("ben", "2026-02-01", "Ben adds", {"shared.py": lines(4, prefix="s") + ben_lines, "ben_only.py": lines(5)}),
            ("eli", "2026-02-05", "Eli owns this", {"legacy.py": lines(30, prefix="e")}),
            ("bot", "2026-02-10", "chore: bump", {"deps.txt": "a\n"}),
            ("bot", "2026-03-10", "chore: bump again", {"deps.txt": "b\n", "core.py": main_text + lines(2, prefix="o")}),
            ("ben", "2026-10-20", "Recent", {"ben_only.py": lines(6)}),
        ])

    def report(self, *extra):
        code, out, err = run_main(ow, [self.repo, "--json", "--as-of", "2026-11-01"] + list(extra))
        self.assertEqual((code, err), (0, ""))
        return json.loads(out)

    def file(self, data, name):
        return [r for r in data["files"] if r["file"] == name][0]

    def test_mailmap_merges_aliases(self):
        data = self.report()
        self.assertEqual(data["summary"]["authors"], 3)       # ava (two emails), ben, eli
        core = self.file(data, "core.py")
        self.assertEqual((core["main_owner"], core["owner_share"], core["basis"]), ("Ava Example", 100.0, "blame"))

    def test_blame_shares_surviving_lines(self):
        shared = self.file(self.report(), "shared.py")
        self.assertEqual(shared["owner_share"], 50.0)
        self.assertEqual(shared["bus_factor"], 1)
        self.assertEqual([a["author"] for a in shared["top_authors"]], ["Ava Example", "Ben Sample"])

    def test_bots_are_excluded(self):
        data = self.report()
        self.assertEqual(data["summary"]["bot_commits_excluded"], 2)
        names = [r["file"] for r in data["files"]]
        self.assertNotIn("deps.txt", names)
        self.assertEqual(self.file(data, "core.py")["commits"], 2)      # the bot's touch of core.py is not counted
        self.assertGreater(data["summary"]["bot_lines_excluded"], -1)

    def test_include_bots(self):
        data = self.report("--include-bots")
        self.assertIn("deps.txt", [r["file"] for r in data["files"]])
        self.assertEqual(data["summary"]["bot_commits_excluded"], 0)

    def test_knowledge_at_risk(self):
        data = self.report()
        risk = [r["file"] for r in data["knowledge_at_risk"]]
        self.assertIn("legacy.py", risk)
        self.assertIn("core.py", risk)       # Ava has not committed since January either
        self.assertNotIn("ben_only.py", risk)
        legacy = [r for r in data["knowledge_at_risk"] if r["file"] == "legacy.py"][0]
        self.assertEqual((legacy["main_owner"], legacy["owner_share"]), ("Eli Former", 100.0))
        self.assertEqual(legacy["owner_last_commit"], "2026-02-05")
        self.assertEqual(legacy["owner_idle_days"], 269)

    def test_inactive_days_threshold(self):
        data = self.report("--inactive-days", "400")
        self.assertEqual(data["knowledge_at_risk"], [])
        self.assertEqual(data["knowledge_at_risk_total"], 0)

    def test_min_share(self):
        data = self.report("--min-share", "1.0")
        self.assertIn("legacy.py", [r["file"] for r in data["knowledge_at_risk"]])
        self.assertNotIn("shared.py", [r["file"] for r in data["knowledge_at_risk"]])

    def test_as_of_changes_idle_days(self):
        code, out, _ = run_main(ow, [self.repo, "--json", "--as-of", "2026-03-01", "--inactive-days", "100"])
        data = json.loads(out)
        self.assertEqual(data["knowledge_at_risk"], [])      # only 24 days since Eli's commit
        self.assertEqual(data["summary"]["commits_scanned"], 5)      # later commits are ignored

    def test_fast_uses_commit_share(self):
        data = self.report("--fast")
        self.assertEqual(data["summary"]["blamed_files"], 0)
        self.assertIsNone(data["summary"]["bus_factor_blamed_lines"])
        self.assertTrue(all(r["basis"] == "commits" for r in data["files"]))
        self.assertEqual(self.file(data, "shared.py")["owner_share"], 50.0)

    def test_explicit_files(self):
        data = self.report("--file", "legacy.py")
        self.assertEqual(data["summary"]["blamed_files"], 1)
        self.assertEqual(self.file(data, "legacy.py")["basis"], "blame")
        self.assertEqual(self.file(data, "core.py")["basis"], "commits")

    def test_missing_blame_target_falls_back(self):
        data = self.report("--file", "nope.py")
        self.assertEqual(data["summary"]["blamed_files"], 0)

    def test_directories(self):
        data = self.report()
        top = dict((r["directory"], r) for r in data["directories"])
        self.assertEqual(top["."]["authors"], 3)
        self.assertEqual(top["."]["bus_factor"], 2)

    def test_markdown(self):
        code, out, _ = run_main(ow, [self.repo, "--as-of", "2026-11-01", "--label", "proj"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("# Ownership: proj\n"))
        self.assertIn("## Knowledge at risk", out)
        self.assertIn("| `legacy.py` | Eli Former | 100.0% | 2026-02-05 | 269 |", out)
        self.assertIn("Do not use this to rank people.", out)
        self.assertNotIn("\r", out)

    def test_fail_at_risk(self):
        args = [self.repo, "--as-of", "2026-11-01", "--fail-at-risk"]
        self.assertEqual(run_main(ow, args + ["1"])[0], 1)
        self.assertEqual(run_main(ow, args + ["99"])[0], 0)

    def test_output_is_deterministic(self):
        self.assertEqual(self.report("--top", "3"), self.report("--top", "3"))

    def test_exclude_author_regex(self):
        data = self.report("--exclude-author", "^Eli")
        self.assertNotIn("legacy.py", [r["file"] for r in data["files"]])


@needs_git
class BlameDetailsTests(unittest.TestCase):
    def test_merge_email_domain(self):
        repo = make_repo([
            ("ava", "2026-01-01", "a", {"f.py": lines(3, prefix="a")}),
            (("Ava E.", "ava@corp.example.org"), "2026-01-02", "b", {"f.py": lines(3, prefix="a") + lines(3, prefix="b")}),
        ])
        code, out, _ = run_main(ow, [repo, "--json", "--as-of", "2026-02-01"])
        self.assertEqual(json.loads(out)["summary"]["authors"], 2)
        code, out, _ = run_main(ow, [repo, "--json", "--as-of", "2026-02-01", "--merge-email-domain", "corp.example.org",
                                     "--merge-email-domain", "example.com"])
        data = json.loads(out)
        self.assertEqual(data["summary"]["authors"], 1)
        self.assertEqual(data["files"][0]["owner_share"], 100.0)

    def test_ignore_revs_skips_a_reformat_commit(self):
        original = "".join("value{} = {}\n".format(i, i) for i in range(10))
        reformatted = "".join("value{}  =  {}\n".format(i, i) for i in range(10))
        path = make_repo([("ava", "2026-01-01", "Init", {"f.py": original})])
        g = GitRepo(path)
        g.write("f.py", reformatted.replace("  =  ", "=").upper())
        sha = g.commit("style: reformat", "ben", "2026-02-01T10:00:00+0000")
        counts, bots = ow.blame_file(path, "f.py", 20.0, None, people())
        self.assertEqual(counts, {"ben@example.com": 10})
        g.write(".git-blame-ignore-revs", sha + "\n")
        counts, bots = ow.blame_file(path, "f.py", 20.0, ".git-blame-ignore-revs", people())
        self.assertEqual(counts, {"ava@example.com": 10})

    def test_blame_ignores_whitespace_only_changes(self):
        path = make_repo([("ava", "2026-01-01", "Init", {"f.py": "a = 1\nb = 2\n"})])
        g = GitRepo(path)
        g.write("f.py", "a  =  1\nb  =  2\n")
        g.commit("whitespace", "ben", "2026-02-01T10:00:00+0000")
        counts, _ = ow.blame_file(path, "f.py", 20.0, None, people())
        self.assertEqual(counts, {"ava@example.com": 2})

    def test_blame_of_a_missing_file_returns_none(self):
        path = make_repo([("ava", "2026-01-01", "Init", {"f.py": "a\n"})])
        self.assertEqual(ow.blame_file(path, "gone.py", 20.0, None, people()), (None, 0))

    def test_blame_counts_bot_lines_separately(self):
        path = make_repo([("ava", "2026-01-01", "Init", {"f.py": "a\nb\n"}),
                          ("bot", "2026-01-02", "bump", {"f.py": "a\nb\nc\n"})])
        counts, bots = ow.blame_file(path, "f.py", 20.0, None, people())
        self.assertEqual((counts, bots), ({"ava@example.com": 2}, 1))


@needs_git
class DemoTests(unittest.TestCase):
    def test_demo_numbers(self):
        code, out, _ = run_main(ow, [demo_repo(), "--json", "--as-of", "2026-11-01"])
        data = json.loads(out)
        self.assertEqual(data["summary"]["authors"], 5)
        self.assertEqual(data["summary"]["bot_commits_excluded"], 5)
        risk = data["knowledge_at_risk"]
        self.assertEqual([r["file"] for r in risk], ["src/shop/legacy_sync.py"])
        self.assertEqual(risk[0]["main_owner"], "Eli Former")
        orders = [r for r in data["files"] if r["file"] == "src/shop/orders.py"][0]
        self.assertEqual(orders["main_owner"], "Ava Example")

    def test_demo_fast_matches_commit_basis(self):
        code, out, _ = run_main(ow, [demo_repo(), "--json", "--as-of", "2026-11-01", "--fast"])
        data = json.loads(out)
        self.assertEqual(data["summary"]["blamed_files"], 0)
        self.assertIn("src/shop/legacy_sync.py", [r["file"] for r in data["knowledge_at_risk"]])


class ErrorTests(unittest.TestCase):
    def test_not_a_repository(self):
        with TempDir() as tmp:
            code, out, err = run_main(ow, [tmp])
        self.assertEqual(code, 2)
        self.assertIn("owners:", err)

    def test_bad_arguments(self):
        self.assertEqual(run_main(ow, [".", "--as-of", "yesterday"])[0], 2)
        self.assertEqual(run_main(ow, [".", "--top", "0"])[0], 2)
        self.assertEqual(run_main(ow, [".", "--min-share", "3"])[0], 2)
        self.assertEqual(run_main(ow, [".", "--exclude-author", "("])[0], 2)

    @needs_git
    def test_empty_repository(self):
        path = scratch_dir()
        GitRepo(path)
        self.assertEqual(run_main(ow, [path])[0], 2)


if __name__ == "__main__":
    unittest.main()
