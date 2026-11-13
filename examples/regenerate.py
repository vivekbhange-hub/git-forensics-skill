#!/usr/bin/env python3
"""Rebuild the synthetic demo history and regenerate (or verify) every file in examples/output/.

  python examples/regenerate.py                     rewrite examples/output/
  python examples/regenerate.py --check             exit 1 if the committed outputs are stale
  python examples/regenerate.py --build-demo DIR    build the demo repository in DIR to try the scripts

The demo is a made-up shop with about 70 commits by invented people (example.com addresses), built
with fixed author and commit dates so every report is byte-for-byte reproducible. The repository is
created in a temporary folder (or in DIR, which is git-ignored when it is examples/demo-repo); no
real history is read. Needs git on the PATH. Standard library only.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "examples" / "output"
DEMO_NAME = "demo-repo"

PEOPLE = {
    "ava": ("Ava Example", "ava@example.com"),
    "ava_old": ("Ava Example", "ava.e@old.example.net"),
    "ben": ("Ben Sample", "ben@example.com"),
    "chen": ("Chen Placeholder", "chen@example.com"),
    "dana": ("Dana Test", "dana@example.com"),
    "eli": ("Eli Former", "eli@example.com"),
    "bot": ("dependabot[bot]", "bot@example.com"),
}

# (output file, skill folder, script, arguments after the repository path)
RUNS = [
    ("hotspots.md", "gitfx-hotspots", "hotspots", ["--top", "10"]),
    ("hotspots.json", "gitfx-hotspots", "hotspots", ["--top", "3", "--json"]),
    ("coupling.md", "gitfx-coupling", "coupling", ["--min-shared", "4", "--min-confidence", "0.6", "--top", "10"]),
    ("coupling-hidden.md", "gitfx-coupling", "coupling", ["--hidden-only", "--min-shared", "4", "--top", "5"]),
    ("owners.md", "gitfx-owners", "owners", ["--as-of", "2026-11-01", "--top", "8"]),
    ("owners-fast.md", "gitfx-owners", "owners", ["--as-of", "2026-11-01", "--fast", "--top", "8"]),
]


def git_available() -> bool:
    return shutil.which("git") is not None


class GitRepo(object):
    """A throwaway repository with deterministic commits (fixed names, emails and dates)."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")

    def env(self, who=None, when=None):
        env = dict(os.environ)
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "LC_ALL": "C"})
        if who:
            name, email = PEOPLE[who] if who in PEOPLE else who
            env.update({"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
                        "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email})
        if when:
            env.update({"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})
        return env

    def git(self, *args, **kw):
        cmd = ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", "-c", "core.quotepath=off",
               "-C", str(self.path)] + list(args)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=self.env(kw.get("who"), kw.get("when")))
        if proc.returncode != 0:
            raise RuntimeError("git {} failed: {}".format(" ".join(args), proc.stderr.decode("utf-8", "replace")))
        return proc.stdout.decode("utf-8", "replace")

    def write(self, rel, text):
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))

    def remove(self, rel):
        (self.path / rel).unlink()

    def move(self, old, new):
        (self.path / new).parent.mkdir(parents=True, exist_ok=True)
        os.replace(str(self.path / old), str(self.path / new))

    def commit(self, message, who, when):
        """Stage everything and commit as `who` (a key of PEOPLE or a (name, email) pair) at `when`."""
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "--no-verify", "-m", message, who=who, when=when)
        return self.git("rev-parse", "HEAD").strip()


class Demo(object):
    """Generates file contents for the demo plan; every line is derived from counters."""

    def __init__(self, repo):
        self.repo = repo
        self.lines = {}
        self.seq = {}

    def _flush(self, path):
        self.repo.write(path, "\n".join(self.lines[path]) + "\n")

    def head(self, path, text):
        self.lines.setdefault(path, []).insert(0, text)
        self._flush(path)

    def grow(self, path, count, depth):
        lines = self.lines.setdefault(path, [])
        for _ in range(count):
            n = self.seq.get(path, 0)
            self.seq[path] = n + 1
            lines.append("    " * (1 + n % depth) + "value_{0} = compute_{0}(item)".format(n))
        self._flush(path)

    def edit(self, path, count):
        lines = self.lines[path]
        rev = self.seq.get(path + "#rev", 0) + 1
        self.seq[path + "#rev"] = rev
        for i in range(count):
            index = 1 + (i * 7 + rev * 3) % (len(lines) - 1)
            indent = lines[index][:len(lines[index]) - len(lines[index].lstrip())]
            lines[index] = "{}value_r{}_{} = recompute(item)".format(indent, rev, i)
        self._flush(path)

    def trim(self, path, count):
        del self.lines[path][1:1 + count]
        self._flush(path)

    def move(self, old, new):
        self.lines[new] = self.lines.pop(old)
        for suffix in ("", "#rev"):      # keep the counters so later edits differ from earlier ones
            if old + suffix in self.seq:
                self.seq[new + suffix] = self.seq.pop(old + suffix)
        self.repo.move(old, new)

    def apply(self, ops):
        for op in ops:
            kind, rest = op.split(":", 1)
            parts = rest.split(":")
            if kind == "grow":
                self.grow(parts[0], int(parts[1]), int(parts[2]))
            elif kind == "edit":
                self.edit(parts[0], int(parts[1]))
            elif kind == "trim":
                self.trim(parts[0], int(parts[1]))
            elif kind == "mv":
                self.move(parts[0], parts[1])
            else:
                raise ValueError(op)


O, P, I, T = "src/shop/orders.py", "src/shop/pricing.py", "billing/invoice.py", "tests/test_orders.py"
C, G, W, L = "src/shop/config.py", "docs/guide.md", "web/templates/cart.html", "src/shop/legacy_sync.py"
U, H = "src/shop/util.py", "src/shop/helpers.py"
PKG, LOCK, VEN = "package.json", "package-lock.json", "vendor/lib.js"
GEN = ["src/shop/adapters/mod_{:02d}.py".format(i) for i in range(35)]

# (date, who, message, operations)
PLAN = [
    ("2026-01-05", "ava_old", "Initial import of the shop",
     ["grow:%s:60:4" % O, "grow:%s:40:3" % P, "grow:%s:30:2" % I, "grow:%s:20:2" % T, "grow:%s:10:1" % C,
      "grow:%s:15:2" % U, "grow:%s:25:2" % W, "grow:%s:20:1" % G, "grow:%s:6:1" % PKG, "grow:%s:200:1" % LOCK]),
    ("2026-01-08", "eli", "Add legacy sync job", ["grow:%s:80:5" % L]),
    ("2026-01-14", "eli", "legacy_sync: add retry loop", ["grow:%s:20:6" % L]),
    ("2026-01-20", "ava_old", "Add order totals", ["grow:%s:30:5" % O, "edit:%s:3" % O, "grow:%s:10:3" % P]),
    ("2026-01-27", "eli", "Fix sync crash on empty batch", ["edit:%s:3" % L]),
    ("2026-02-02", "ben", "Fix rounding bug in order totals",
     ["edit:%s:4" % O, "edit:%s:2" % P, "edit:%s:2" % I, "edit:%s:2" % T]),
    ("2026-02-10", "eli", "legacy_sync: support partial batches", ["grow:%s:25:6" % L]),
    ("2026-02-16", "chen", "Add coupon support",
     ["grow:%s:25:5" % O, "grow:%s:15:3" % P, "grow:%s:5:2" % I, "grow:%s:8:2" % T]),
    ("2026-02-20", "ben", "Vendor lib.js 2.1", ["grow:%s:400:1" % VEN]),
    ("2026-02-24", "eli", "Fix duplicate rows after retry", ["edit:%s:4" % L]),
    ("2026-03-01", "bot", "chore(deps): bump framework to 4.2", ["edit:%s:2" % PKG, "edit:%s:30" % LOCK]),
    ("2026-03-03", "ava", "Fix coupon stacking regression", ["edit:%s:5" % O, "edit:%s:3" % T, "edit:%s:2" % I]),
    ("2026-03-05", "eli", "legacy_sync: log batch ids", ["grow:%s:6:4" % L]),
    ("2026-03-10", "eli", "Document sync job", ["grow:%s:10:1" % G, "edit:%s:1" % L]),
    ("2026-03-12", "chen", "Fix util crash on empty input", ["edit:%s:2" % U]),
    ("2026-03-20", "ben", "Hotfix: negative totals on refunds", ["edit:%s:3" % O, "edit:%s:3" % I, "grow:%s:4:2" % T]),
    ("2026-04-01", "ava", "util: add slugify", ["grow:%s:6:2" % U]),
    ("2026-04-02", "ava", "Fix typo in legacy_sync", ["edit:%s:1" % L]),
    ("2026-04-08", "ava", "Add shipping estimate", ["grow:%s:20:6" % O, "grow:%s:6:3" % P, "grow:%s:5:2" % W]),
    ("2026-04-15", "bot", "chore(deps): bump test runner", ["edit:%s:2" % PKG, "edit:%s:25" % LOCK]),
    ("2026-04-21", "chen", "Fix tax on shipping", ["edit:%s:4" % O, "edit:%s:3" % I, "edit:%s:2" % T]),
    ("2026-05-05", "dana", "Rename util to helpers", ["mv:%s:%s" % (U, H)]),
    ("2026-05-05", "ava", "Invoice footer text", ["edit:%s:2" % I]),
    ("2026-05-12", "dana", "Refactor order state handling", ["grow:%s:15:5" % O, "trim:%s:10" % O, "grow:%s:6:2" % T]),
    ("2026-05-20", "chen", "Add config option for currency", ["grow:%s:4:1" % C, "grow:%s:3:1" % G]),
    ("2026-05-27", "dana", "Fix crash when cart is empty", ["edit:%s:2" % O, "edit:%s:2" % T]),
    ("2026-06-02", "ben", "Fix helper edge case", ["edit:%s:2" % H]),
    ("2026-06-10", "ava", "Add gift wrap option",
     ["grow:%s:12:6" % O, "edit:%s:3" % P, "grow:%s:6:2" % W, "grow:%s:4:2" % I]),
    ("2026-06-12", "chen", "Add config option for locale", ["grow:%s:3:1" % C, "grow:%s:2:1" % G]),
    ("2026-06-17", "ben", "style: reformat adapters", ["edit:%s:1" % g for g in GEN]),
    ("2026-06-24", "ben", "Fix double charge on retry", ["edit:%s:3" % O, "edit:%s:2" % I, "edit:%s:2" % T]),
    ("2026-06-30", "bot", "chore(deps): bump linter", ["edit:%s:1" % PKG, "edit:%s:20" % LOCK]),
    ("2026-07-02", "dana", "Pricing: round to cents", ["edit:%s:3" % P]),
    ("2026-07-15", "chen", "Revert gift wrap pricing change", ["edit:%s:4" % O, "edit:%s:4" % P, "edit:%s:3" % W]),
    ("2026-07-22", "ava", "Add config option for retries", ["grow:%s:3:1" % C, "grow:%s:2:1" % G]),
    ("2026-07-30", "ben", "Invoice layout tweaks", ["grow:%s:5:2" % I]),
    ("2026-08-01", "ben", "Update vendored lib.js", ["edit:%s:100" % VEN]),
    ("2026-08-04", "ava", "Add loyalty points", ["grow:%s:18:6" % O, "grow:%s:6:2" % I, "grow:%s:5:2" % T]),
    ("2026-08-12", "bot", "chore(deps): bump http client", ["edit:%s:1" % PKG, "edit:%s:25" % LOCK]),
    ("2026-08-19", "dana", "Fix loyalty points rounding", ["edit:%s:3" % O, "edit:%s:2" % I, "edit:%s:3" % T]),
    ("2026-08-26", "chen", "Pricing: cache tier lookups", ["grow:%s:8:3" % P]),
    ("2026-09-02", "chen", "Add config option for cache ttl", ["grow:%s:3:1" % C, "grow:%s:2:1" % G]),
    ("2026-09-09", "ava", "Support partial shipments", ["grow:%s:22:6" % O, "grow:%s:8:2" % I, "grow:%s:6:2" % T]),
    ("2026-09-16", "bot", "chore(deps): bump date library", ["edit:%s:1" % PKG, "edit:%s:20" % LOCK]),
    ("2026-09-23", "ben", "Style cart page", ["grow:%s:4:2" % W]),
    ("2026-09-30", "ben", "Fix partial shipment totals bug",
     ["edit:%s:5" % O, "edit:%s:3" % I, "edit:%s:3" % T, "edit:%s:2" % P]),
    ("2026-10-07", "chen", "Add config option for log level", ["grow:%s:3:1" % C, "grow:%s:2:1" % G]),
    ("2026-10-14", "ava", "Tidy order module", ["edit:%s:2" % O]),
    ("2026-10-20", "dana", "Pricing: document tiers", ["grow:%s:4:3" % P]),
    ("2026-10-27", "dana", "Fix regression in coupon validation", ["edit:%s:3" % O, "edit:%s:2" % T]),
]


def build_demo(dest) -> None:
    """Create the synthetic repository in `dest` (an empty or missing folder)."""
    repo = GitRepo(dest)
    demo = Demo(repo)
    repo.write(".mailmap", "Ava Example <ava@example.com> <ava.e@old.example.net>\n")
    for number, (date, who, message, ops) in enumerate(PLAN):
        demo.apply(ops)
        if number == 0:      # the first commit also gives orders and its test a visible reference
            demo.head(O, "from shop import pricing")
            demo.head(T, "from shop import orders")
        repo.commit(message, who, date + "T10:00:00+0000")
        if message == "Vendor lib.js 2.1":      # 35 small files in one commit; reformatted in June
            for g in GEN:
                demo.grow(g, 5, 2)
            repo.commit("Add adapter stubs", "ben", date + "T12:00:00+0000")


def _load(skill: str, script: str):
    path = ROOT / "skills" / skill / "{}.py".format(script)
    spec = importlib.util.spec_from_file_location("_regen_{}".format(script), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render(skill: str, script: str, argv: list) -> bytes:
    """Run one script's main() and return what it printed, as UTF-8 with LF."""
    module = _load(skill, script)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = module.main(argv)
    if code != 0:
        raise RuntimeError("{} {} exited with {}".format(script, " ".join(argv), code))
    return buffer.getvalue().replace("\r\n", "\n").encode("utf-8")


def generate(out: Path) -> list:
    """Build the demo history in a temp folder and write every report into `out`."""
    if not git_available():
        raise RuntimeError("git is not installed")
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        demo_dir = Path(tmp) / DEMO_NAME
        build_demo(demo_dir)
        for name, skill, script, argv in RUNS:
            (out / name).write_bytes(render(skill, script, [str(demo_dir)] + argv))
    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())


def compare(expected_dir: Path, actual_dir: Path) -> list:
    """Return a list of differences between two output folders."""
    problems = []
    expected = {p.relative_to(expected_dir).as_posix() for p in expected_dir.rglob("*") if p.is_file()}
    actual = {p.relative_to(actual_dir).as_posix() for p in actual_dir.rglob("*") if p.is_file()}
    for name in sorted(expected ^ actual):
        problems.append("{}: {}".format(name, "missing from regenerated output" if name in expected else "not committed"))
    for name in sorted(expected & actual):
        if (expected_dir / name).read_bytes() != (actual_dir / name).read_bytes():
            problems.append("{}: content differs".format(name))
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="verify instead of rewriting")
    parser.add_argument("--build-demo", metavar="DIR", help="build the demo repository in DIR and stop")
    args = parser.parse_args(argv)
    if not git_available():
        print("git is not installed; the demo history cannot be built", file=sys.stderr)
        return 2
    if args.build_demo:
        target = Path(args.build_demo)
        if target.exists() and any(target.iterdir()):
            print("{} exists and is not empty".format(target), file=sys.stderr)
            return 2
        build_demo(target)
        print("built the demo repository in {}".format(target))
        return 0
    if not args.check:
        for name in generate(OUTPUT):
            print("wrote examples/output/{}".format(name))
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        generate(Path(tmp))
        problems = compare(OUTPUT, Path(tmp))
    for problem in problems:
        print(problem)
    print("examples/output is up to date" if not problems else "{} stale file(s)".format(len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
