"""Build deterministic git repositories for tests (needs git on the PATH; tests skip without it)."""
from __future__ import annotations

import atexit
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from _load import ROOT, load_path

regen = load_path(ROOT / "examples" / "regenerate.py", "regenerate_for_tests")
GitRepo = regen.GitRepo
HAVE_GIT = regen.git_available()
needs_git = unittest.skipUnless(HAVE_GIT, "git is not installed: skipping tests that build a repository")

_cleanup = []


def _on_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path):
    """Delete a folder that may hold read-only git objects."""
    shutil.rmtree(path, onerror=_on_error)


def _remove_all():
    for folder in _cleanup:
        shutil.rmtree(folder, onerror=_on_error)


atexit.register(_remove_all)


def scratch_dir() -> str:
    """A temporary folder that is removed when the test process exits (git objects are read-only)."""
    folder = tempfile.mkdtemp(prefix="gitfx-test-")
    _cleanup.append(folder)
    return folder


def make_repo(commits, name="proj") -> str:
    """Create a repo from [(who, date, message, {path: text or None})]; return its path.

    `who` is a key of regen.PEOPLE or a (name, email) pair, `date` looks like 2026-03-01 (10:00 UTC),
    a text of None deletes the file, and ("mv", old) as the value renames `old` to the key.
    """
    path = Path(scratch_dir()) / name
    repo = GitRepo(path)
    for who, date, message, files in commits:
        for rel, text in files.items():
            if text is None:
                repo.remove(rel)
            elif isinstance(text, tuple) and text[0] == "mv":
                repo.move(text[1], rel)
            elif isinstance(text, bytes):
                target = path / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(text)
            else:
                repo.write(rel, text)
        repo.commit(message, who, date + "T10:00:00+0000")
    return str(path)


_demo = {}


def demo_repo() -> str:
    """The synthetic shop history from examples/regenerate.py, built once per test process."""
    if "path" not in _demo:
        path = Path(scratch_dir()) / regen.DEMO_NAME
        regen.build_demo(path)
        _demo["path"] = str(path)
    return _demo["path"]


def lines(n, indent="    ", prefix="x"):
    """n distinct code-like lines."""
    return "".join("{}{}{} = {}\n".format(indent, prefix, i, i) for i in range(n))
