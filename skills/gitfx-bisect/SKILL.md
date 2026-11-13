---
name: gitfx-bisect
description: >-
  A disciplined procedure for finding the commit that introduced a bug with git bisect: write a
  deterministic failing test first, pick known good and bad commits, automate with git bisect
  run, handle untestable commits with skip, treat flaky tests properly, and record the culprit
  commit and why it broke things. Use when the user says "which commit broke this", "git
  bisect", "find the regression", "it worked last month", "track down when this started
  failing", or "bisect with a flaky test".
argument-hint: "[symptom] [known good commit or tag]"
---

# gitfx-bisect: find the commit, then understand it

`git bisect` finds a culprit in about log2(n) steps, but only if every step answers the same
question reliably. Most failed bisects fail on the question, not on git. This skill makes the
question deterministic first, then lets git do the search. It has no script of its own.

## Inputs

- The symptom in one sentence, and how to see it (a command, a test, a URL).
- A commit, tag or date where it worked (good) and one where it fails (bad, usually `HEAD`).
- Permission to check out other commits in the working tree: bisect moves `HEAD`. Ask before
  starting, and make sure the tree is clean (`git status --short` prints nothing). Do not run it
  in a repository the user does not own or is not authorized to change.
- Commands below say `python3`; on Windows use `python` (or `py -3`).

## Outputs

- `gitfx/bisect-report.md`: symptom, the exact test command, good and bad commits, the culprit
  commit hash, subject and date, the files it touched, the reason it broke things, and the fix.
- In chat: the culprit in one sentence, with the evidence, and the state the repo was left in.

## Steps

1. **Write the test first.** A script or test that exits 0 when the bug is absent and 1 to 124
   when it is present, runs in under a minute, needs no network or manual step and does not
   depend on the current time or random data. Run it on `HEAD` (must fail) and on the good
   commit (must pass) before bisecting. If either is wrong, fix the test, not the search.

2. **Keep the test outside the tree**, for example `/tmp/bisect_test.sh` (on Windows a `.py` file
   in a temp folder), so checking out old commits does not delete it. It must build whatever it
   needs itself, because old commits may need an older setup step.

3. **Start the search**:
   ```
   git bisect start
   git bisect bad HEAD
   git bisect good <good-commit>
   git bisect run python3 /tmp/bisect_test.py
   ```
   On Windows use `python`. Git prints "<hash> is the first bad commit" at the end.

4. **Handle commits that cannot be tested.** If a commit does not build or the test cannot run,
   the script must use exit code 125 so bisect skips it; `git bisect skip` does it by hand. Too
   many skips and git reports a range of candidates instead of one commit; say so, do not guess.
   Never exit 1 for "could not build": that marks the commit bad and corrupts the result.

5. **Treat flaky tests as the main risk.** Run the test 5 times on the bad commit and 5 on the
   good one before starting. If it is not 5 of 5 and 0 of 5, make it deterministic (fix seeds,
   freeze time, isolate state) or loop inside the script and require N consecutive failures. A
   flaky answer sends bisect down the wrong half silently.

6. **Verify the culprit.** `git show <hash>` and read the diff. Check out its parent, run the test
   (passes), then the commit (fails). Revert it on a scratch branch to confirm the bug disappears.
   A merge commit as culprit means the bug is an interaction; bisect the branch's own commits.

7. **Leave the repo clean**: `git bisect reset` returns to the original branch. Check
   `git status`. Save the log first with `git bisect log > gitfx/bisect.log` for the report.

8. **Record why.** In the report, state what the commit changed, why that causes the symptom,
   whether the commit was wrong or exposed an older problem, and the smallest fix. Link the
   hotspot or coupling data if it explains why the area keeps breaking.

## Decision rules

- Tests that need a build step go inside the bisect script, with the build failing as exit 125.
- A good commit that is not really good (the bug existed but was masked) makes bisect land on
  the commit that unmasked it. Check the result against step 6 before accepting it.
- Use `git bisect start --first-parent` when the history is merge-heavy and a pull request is
  an acceptable answer; then bisect inside it if the user needs a commit.
- If the history has a long run of unbuildable commits, narrow the range with
  `git log --oneline` and known release tags first.
- Use `git bisect replay gitfx/bisect.log` to repeat a run; use `git bisect visualize` only to
  look, never to decide.

## What NOT to do

- Do not bisect without a deterministic test, and do not judge commits by eye or by hand-run
  commands that change between steps.
- Do not start with uncommitted work in the tree, and do not leave the repo in bisect state.
- Do not use exit code 1 for unbuildable commits, or 125 for a real failure.
- Do not push, force-push, rebase or alter history as part of a bisect.
- Do not blame the author of the culprit commit; record what changed and why, not who.
