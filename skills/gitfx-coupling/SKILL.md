---
name: gitfx-coupling
description: >-
  Finds files that change together in git history (temporal coupling) and separates the expected
  pairs, such as a module and its test, from hidden dependencies: files in different directories
  that move together but never mention each other. Explains the likely cause of each strong pair
  and suggests an extraction or an explicit interface. Use when the user says "what changes
  together", "hidden dependencies", "why does changing X always break Y", "find coupled files",
  "which modules are entangled", or "what should I extract".
argument-hint: "[path to repo] [--since \"12 months ago\"]"
---

# gitfx-coupling: what really depends on what

Import graphs show the dependencies you declared. Version control shows the ones you have:
files that are edited in the same commit again and again. `coupling.py` counts those pairs from
`git log` and flags the ones with no visible link between them.

## Inputs

- A path inside a git repository (default: the current folder).
- Optional: a window (`--since "12 months ago"`), a sub-tree (`--path src`), thresholds
  `--min-shared` (default 3) and `--min-confidence` (default 0.5), `--max-files` (default 30).
- Commands below say `python3`; on Windows use `python` (or `py -3`). `git` must be on the PATH.

## Outputs

- `gitfx/coupling.md` (or the path the user prefers): pairs with shared commits, support,
  confidence both ways, cross-module and reference flags, and clusters.
- In chat: the 3 to 5 pairs that matter, the likely cause of each, and one concrete change each.

## Steps

1. **Confirm permission.** Ask once whether the user owns or is authorized to analyse this
   repository. If not, stop.

2. **Run the script** over a recent window:
   ```
   python3 "${CLAUDE_SKILL_DIR}/coupling.py" . --since "12 months ago" --top 25 -o gitfx/coupling.md
   python3 "${CLAUDE_SKILL_DIR}/coupling.py" . --since "12 months ago" --hidden-only --top 10
   ```
   The second command keeps only cross-module pairs with no visible reference, test pairs
   excluded. Commits that touch more than `--max-files` files are skipped as bulk edits.

3. **Read the header.** Check "commits counted" and "skipped bulk". If most commits were skipped
   the team commits in large batches and the pairs will be thin; raise `--max-files` and say so.

4. **Read confidence in both directions.** `A->B` is the share of A's commits that also touched
   B. A high value one way and low the other means B is a dependent of A (change A and you must
   touch B), not a true twin. Both high means a shared concept that deserves a name.

5. **Judge each strong pair**, opening the two files briefly:
   - **Test and code**: expected; ignore unless the test also moves with a third, unrelated file.
   - **Same directory, mentioned**: ordinary cohesion; probably fine.
   - **Cross-module, no reference**: the interesting case. Look for the cause: duplicated
     business rule, a shared data shape or schema, a config key, a naming convention, a manual
     "keep these in sync" step, a template and the code that fills it.

6. **Suggest the smallest honest fix** for each hidden pair: extract the shared rule into one
   module both import, introduce an explicit interface or type for the shared shape, generate one
   side from the other, or add a test that fails when the two drift apart.

7. **Name the clusters.** The "Clusters" section joins pairs into groups. A cluster spanning
   three or more top-level directories is a candidate for a boundary discussion.

## Decision rules

- A pair needs at least `--min-shared` commits; three coincidences are still coincidences. For a
  small repo raise the bar to 4 or 5 rather than lowering confidence.
- The reference check compares file name stems as text. "Mentioned" can be a false link (a
  generic stem like `utils`), "none seen" can be a false gap (dynamic loading, config keys,
  string-built paths). Open both files before calling it a hidden dependency.
- Squash merges glue unrelated files into one commit and inflate coupling; if the history is all
  squashes, say the evidence is weak.
- Docs, changelogs and generated files couple to everything; use `--exclude` rather than
  explaining them.
- Renames are followed only when git detects them; a heavily edited move splits history.
- Coupling that is intended (a library and its adapter) is not a defect. Recommend a change only
  when the cost of the coupling is visible, for example repeated fix commits across the pair.

## What NOT to do

- Do not claim a causal dependency from co-change alone; report it as a lead to verify.
- Do not paste git history into the conversation, and do not analyse repositories the user is not
  authorized to read.
- Do not suggest a large restructuring from one pair; propose the smallest extraction that can be
  reviewed in one pull request.
- Do not use the output to say which person causes coupling. Pairs describe files.
- Do not invent counts or confidence values; quote the report.
