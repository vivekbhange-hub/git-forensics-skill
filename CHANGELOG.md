# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-13

### Added

- Five skills: `gitfx-hotspots`, `gitfx-coupling`, `gitfx-owners`, `gitfx-story` and `gitfx-bisect`.
- Two read-only agents: `hotspot-analyst` and `ownership-skeptic`.
- Helper scripts (standard library and `git` only, streaming, read-only): `hotspots.py` (churn x
  complexity ranking with fix share and rename following), `coupling.py` (temporal coupling with
  support, directional confidence, cross-module and hidden-dependency flags, clusters) and
  `owners.py` (bus factor, knowledge at risk, `git blame` with a commit-share fallback, alias
  merging through `.mailmap` and `--merge-email-domain`, bot exclusion).
- A synthetic shop history (about 50 commits, invented people, fixed dates) rebuilt by
  `examples/regenerate.py` in a temporary folder, with reports under `examples/output/` checked
  byte-for-byte by the test suite.
- CI on Linux, Windows and macOS with Python 3.9, 3.12 and 3.13.
