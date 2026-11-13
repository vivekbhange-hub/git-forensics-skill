---
name: gitfx-owners
description: >-
  Reports who owns which code and what happens if they leave: author share per file and top-level
  directory from surviving lines (git blame) or commits, bus factor, and files whose main owner
  has not committed for months (knowledge at risk). Merges aliases through .mailmap and email
  domains and leaves bots out. Use when the user says "what is our bus factor", "who knows this
  code", "knowledge at risk", "who owns this module", "what do we lose if she leaves", or "who
  should review changes to this directory".
argument-hint: "[path to repo] [--as-of YYYY-MM-DD]"
---

# gitfx-owners: where knowledge is concentrated

A file written by one person who has left is a risk you can measure. `owners.py` blames the most
changed files, shares the surviving lines out by author, and lists files whose main owner has been
silent for `--inactive-days`. It measures commits, not skill, and it is not a performance tool.

## Inputs

- A path inside a git repository (default: the current folder). A shallow clone gives wrong
  owners; check `git rev-parse --is-shallow-repository`.
- Optional: `--since "24 months ago"` for commit shares, `--as-of 2026-11-01` to fix "today",
  `--inactive-days 180`, `--fast` (no blame), `--file PATH` (blame exactly these files),
  `--merge-email-domain corp.example.com`, `--exclude-author REGEX`.
- Commands below say `python3`; on Windows use `python` (or `py -3`). `git` must be on the PATH.

## Outputs

- `gitfx/owners.md` (or the path the user prefers): repository bus factor, directory table,
  most-changed files with owner and share, and the knowledge-at-risk table.
- In chat: the bus factor with its basis, the 3 to 5 knowledge-at-risk files, and a suggested
  handover action for each (pairing, docs, a review rota), phrased about files and teams.

## Steps

1. **Confirm permission.** Ask once whether the user owns or is authorized to analyse this
   repository. This report contains names and email-derived identities of colleagues; if the repo
   is not the user's to analyse, stop.

2. **Check the identity hygiene** before running: is there a `.mailmap`? Does the team commit
   from both a work and a personal address? If so, add `--merge-email-domain` for each domain or
   suggest a `.mailmap`. Is there a `.git-blame-ignore-revs`? The script uses it automatically.

3. **Run the script**:
   ```
   python3 "${CLAUDE_SKILL_DIR}/owners.py" . --since "24 months ago" --top 15 -o gitfx/owners.md
   ```
   On a very large repository add `--fast`, or pass the hotspot files with repeated `--file`.
   Blame that exceeds `--blame-timeout` falls back to commit share and the header says so.

4. **Read the header.** Commits scanned, bot commits excluded, number of authors after merging.
   An author count that looks too high usually means unmerged aliases.

5. **Interpret the bus factor.** It is the smallest number of authors covering 50 percent. 1 means
   one person holds most of it. Read it by directory first, then by file; a bus factor of 1 in a
   rarely changed vendor shim matters less than in the payment module.

6. **Interpret knowledge at risk.** A file is listed when its main owner holds at least
   `--min-share` of it and has made no commit anywhere for `--inactive-days`. Idle can mean
   left, on leave or moved teams; say you do not know which, and suggest asking the team.

7. **Say the limit out loud.** State once, in the report you give the user: this measures commits,
   not skill or understanding, and must not be used to rank or judge people.

## Decision rules

- Blame basis counts surviving lines; commit basis counts commits in the window. Do not compare
  a number from one basis with a number from the other.
- A main owner at 30 percent is not an owner. Report a share under 50 percent as "no clear owner".
- Squash merges credit whoever merged; mass reformats and vendor drops can capture lines. If
  one author owns many files with near-identical timestamps, suspect that and consider
  `--ignore-revs` or the `ownership-skeptic` agent before drawing conclusions.
- Window matters: commit shares from a short window hide the person who wrote the file years ago;
  blame sees them. Prefer blame for the risk question.
- Findings go to teams and files. Name a person only where the report names them, never in a
  summary about performance, productivity or "who to blame".
- `--fail-at-risk N` exits 1 when N or more files are at risk; use it as a reminder in CI, not a
  gate.

## What NOT to do

- Do not use the numbers for performance reviews, ranking, bonuses or layoffs, and do not
  produce a leaderboard of authors.
- Do not analyse repositories the user is not authorized to read, and do not post the report
  outside the team without removing names.
- Do not treat bots, merge commits or a single reformat as people who know the code.
- Do not claim someone has left from silence in the log.
- Do not invent shares, dates or idle days; quote the report.
