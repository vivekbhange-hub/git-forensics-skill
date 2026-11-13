---
name: gitfx-story
description: >-
  Writes a one-page "state of this codebase" briefing from git history for a newcomer, a new tech
  lead or an acquirer: the top hotspots, the coupling clusters, the ownership risks and five
  suggested first reads. It runs the three forensics scripts and reads only their reports. Use
  when the user says "brief me on this codebase", "state of this repo", "onboarding overview",
  "due diligence on this code", "where should a new hire start reading", or "give me the story of
  this repository".
argument-hint: "[path to repo]"
---

# gitfx-story: the codebase on one page

A new reader needs to know three things fast: where the trouble is, what is secretly connected,
and whose head holds what. This skill runs the three analysis scripts that live in the sibling
skill folders and turns their reports into one page. It adds no script of its own.

## Inputs

- A path inside a git repository (default: the current folder), full history, not shallow.
- Optional: the reader (new hire, tech lead, acquirer), a window (default `--since "12 months
  ago"`), and the question they care about most.
- This skill calls scripts from sibling skill folders, so install the whole pack, not this
  skill alone. Commands below say `python3`; on Windows use `python` (or `py -3`).

## Outputs

- `gitfx/story.md` (or the path the user prefers): at most one page with five parts: overview,
  hotspots, coupling, ownership and first reads.
- In chat: the three sentences the reader should remember, and what was not checked.

## Steps

1. **Confirm permission.** Ask once whether the user owns or is authorized to analyse this
   repository. For due diligence, the seller must have given access. If not, stop.

2. **Check the ground.** `git rev-parse --is-shallow-repository` (must print `false`),
   `git log --oneline | wc -l` for size (on Windows count with `git rev-list --count HEAD`),
   and the first and last commit dates. Note the age and the commit rate in one sentence.

3. **Run the three scripts** (sibling folders, relative to this skill):
   ```
   python3 "${CLAUDE_SKILL_DIR}/../gitfx-hotspots/hotspots.py" . --since "12 months ago" --top 10 -o gitfx/hotspots.md
   python3 "${CLAUDE_SKILL_DIR}/../gitfx-coupling/coupling.py" . --since "12 months ago" --top 15 -o gitfx/coupling.md
   python3 "${CLAUDE_SKILL_DIR}/../gitfx-owners/owners.py" . --since "24 months ago" --top 10 -o gitfx/owners.md
   ```
   If a script exits 2, read its message; the usual cause is a path that is not a repository.

4. **Read the three reports, not the history.** Open the top two or three hotspot files and the
   strongest hidden coupling pair, briefly, so each claim in the page rests on something seen.

5. **Write the page** in this order, each part short:
   - **Overview**: age, size, commits per month, number of active authors, main languages.
   - **Hotspots**: top 3 to 5 files, one line of why each (churn, size, fix share).
   - **Coupling**: the clusters, and the 1 to 3 hidden dependencies a newcomer will trip over.
   - **Ownership**: repository bus factor, directories with a bus factor of 1, files at risk,
     phrased about teams and files.
   - **First reads**: exactly five files, ordered, each with a reason. Pick a mix: the most
     central hotspot, the entry point, one end of the strongest hidden pair, the test that
     covers the hotspot, and a file owned by someone leaving. Say what to look for in each.

6. **State the confidence and the gaps.** One line each: what the window was, what the
   scripts cannot see (squash merges, renamed history, vendored code), and what you did not
   check (runtime behaviour, tests passing, dependency age).

## Decision rules

- One page means one page. Drop the long tail; point to the three report files for the rest.
- For an acquirer, lead with risk (ownership and hotspots with high fix share) and be explicit
  that history shows past effort, not current quality.
- For a new hire, lead with first reads and the hidden dependencies.
- If the three reports disagree (a hotspot nobody owns, a hidden pair across the hotspots), that
  disagreement is the finding; do not smooth it over.
- Very young repos (under about 50 commits) or all-squash histories give weak signals; say so
  at the top instead of at the end.
- Per-author names appear only where `owners.md` names them and only in the ownership part; the
  rest of the page talks about files and teams.

## What NOT to do

- Do not read the git history into the conversation; use the reports and a few files.
- Do not analyse a repository the user is not authorized to read, or share the page outside the
  intended audience without checking it for names.
- Do not rank people, estimate productivity or write anything usable for a performance review.
- Do not pad the page with generic advice (write more tests, reduce complexity); every line
  must trace to a report row or a file you opened.
- Do not run the scripts on a different repository than the one the user named.
