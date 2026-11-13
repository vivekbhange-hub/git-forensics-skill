---
name: gitfx-hotspots
description: >-
  Ranks the files in a git repository that are both changed often and expensive to change (churn
  times size and nesting), shows commits, lines, authors and fix share for each, explains why each
  one is a hotspot and says where refactoring or tests would pay off most. Reads git history only
  and never loads it into the conversation. Use when the user says "where is this codebase
  fragile", "find the hotspots", "which files change the most", "what should we refactor first",
  "where do bugs cluster", or "which files need tests".
argument-hint: "[path to repo] [--since \"12 months ago\"]"
---

# gitfx-hotspots: the files that cost you the most

Code that is complicated and also changes every week is where defects and delays collect. Code
that is complicated but never changes is a cost you can leave alone. `hotspots.py` ranks files by
both at once, from `git log` alone, so you do not read history into the conversation.

## Inputs

- A path inside a git repository (default: the current folder). Full history is better than a
  shallow clone; check `git rev-parse --is-shallow-repository` and say so if it prints `true`.
- Optional: a window (`--since "12 months ago"`), a sub-tree (`--path src`), extra `--exclude`
  globs for generated code the defaults miss.
- Commands below say `python3`; on Windows use `python` (or `py -3`). `git` must be on the PATH.

## Outputs

- `gitfx/hotspots.md` (or the path the user prefers): the report from the script.
- In chat: the top 5 to 10 files with one sentence of why each ranks, one suggested action each
  (split, add tests, leave alone), and the caveats that apply.

## Steps

1. **Confirm permission.** Ask once whether the user owns or is authorized to analyse this
   repository. Commit history can contain names and email addresses of colleagues; if the repo
   belongs to someone else, stop.

2. **Pick a window.** Recent history says more about today than a decade ago. Start with
   `--since "12 months ago"`; use full history only for a young repo or a stable one.

3. **Run the script**:
   ```
   python3 "${CLAUDE_SKILL_DIR}/hotspots.py" . --since "12 months ago" --top 20 -o gitfx/hotspots.md
   ```
   Use `--json` if you want to post-process. Defaults already skip lockfiles, vendored and
   generated code, minified files and binaries; add `--exclude "docs/"` for the rest.

4. **Read the header first.** Commits scanned, files ranked, window. If it scanned few commits,
   the repo may be shallow or the window too tight; widen it before concluding anything.

5. **Explain each top file** using its row: commits and authors (how contested), lines and mean
   indent (how heavy), fix share (how many of its commits were repairs). Open the file and read
   its structure, not the whole body, so the explanation names real things: a 900-line function,
   a switch that grows with every feature, a class that mixes parsing and persistence.

6. **Sanity-check with fix share.** A hotspot with a high fix share is probably fragile. A
   hotspot with a low one may simply be a busy file, like a routing table or a changelog:
   high churn and low risk. Say which one it is, and why.

7. **Propose where effort pays off.** For each of the top few, one of:
   - add characterisation tests first (high fix share, no tests nearby),
   - split by reason to change (many authors, many unrelated commit subjects),
   - leave alone (large, rarely changed, low fix share),
   - fix the process, not the file (churn comes from one recurring chore).
   Then hand off: `gitfx-coupling` to see what else moves with the top file, `gitfx-owners` to see
   who knows it.

## Decision rules

- The score is churn percentile times complexity percentile. Two files with similar scores are
  not meaningfully ordered; talk about the top cluster, not rank 3 versus rank 4.
- Indentation is a proxy, not cyclomatic complexity. Flat generated tables look simple and long
  files with tiny functions look heavy; check by reading before you recommend a refactor.
- Few commits in the window (under about 3 for most files) makes fix share noise. Say so.
- Squash-merge workflows hide fixes inside feature subjects, so fix share understates; very vague
  subjects ("update", "wip") do the same. Say it when the log looks like that.
- A file renamed with large edits looks new. If a top file is suspiciously young, check
  `git log --follow -- <file>` for its real history.
- `--fail-above 80` makes the script exit 1 when a hotspot is that high; use it in CI only after
  the team has agreed on a baseline.

## What NOT to do

- Do not paste git history or diffs into the conversation; rely on the report and open files
  selectively.
- Do not analyse a repository the user is not authorized to read, and do not publish the report
  outside the team without checking it for names or internal paths.
- Do not turn file-level findings into judgements about the people who edited the files.
- Do not recommend a rewrite from a score. Recommend a first step that can be checked.
- Do not invent numbers or explanations; everything you state comes from the report or from a
  file you actually opened.
