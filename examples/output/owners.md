# Ownership: demo-repo

- Window: all history
- As of: 2026-11-01 (a person is inactive after 180 days without a commit)
- Commits scanned: 51 (5 bot commits excluded); authors after merging aliases: 5
- Repository bus factor by commits: 3
- Bus factor by surviving lines in the 8 blamed files: 2

## Directories (share of commits)

| Directory | Files | Commits | Authors | Bus factor | Main owner | Share |
|---|--:|--:|--:|--:|---|--:|
| `src` | 40 | 40 | 5 | 2 | Ava Example | 27.5% |
| `billing` | 1 | 14 | 4 | 2 | Ava Example | 42.9% |
| `tests` | 1 | 14 | 4 | 2 | Ava Example | 28.6% |
| `docs` | 1 | 7 | 3 | 1 | Chen Placeholder | 57.1% |
| `web` | 1 | 5 | 3 | 1 | Ava Example | 60.0% |
| `.` | 2 | 1 | 1 | 1 | Ava Example | 100.0% |

## Most-changed files

| File | Commits | Authors | Bus factor | Main owner | Share | Basis | Owner last commit |
|---|--:|--:|--:|---|--:|---|---|
| `src/shop/orders.py` | 19 | 4 | 1 | Ava Example | 63.7% | blame | 2026-10-14 |
| `billing/invoice.py` | 14 | 4 | 1 | Ava Example | 60.3% | blame | 2026-10-14 |
| `tests/test_orders.py` | 14 | 4 | 1 | Ava Example | 50.0% | blame | 2026-10-14 |
| `src/shop/pricing.py` | 11 | 4 | 1 | Ava Example | 54.2% | blame | 2026-10-14 |
| `src/shop/legacy_sync.py` | 8 | 2 | 1 | Eli Former | 99.2% | blame | 2026-03-10 |
| `docs/guide.md` | 7 | 3 | 1 | Ava Example | 53.7% | blame | 2026-10-14 |
| `src/shop/config.py` | 6 | 2 | 1 | Ava Example | 50.0% | blame | 2026-10-14 |
| `web/templates/cart.html` | 5 | 3 | 1 | Ava Example | 82.5% | blame | 2026-10-14 |

## Knowledge at risk

| File | Main owner | Share | Owner last commit | Idle days | Commits | Basis |
|---|---|--:|---|--:|--:|---|
| `src/shop/legacy_sync.py` | Eli Former | 99.2% | 2026-03-10 | 236 | 8 | blame |

Basis `blame` counts lines that survive at HEAD; `commits` counts commits in the window. Both measure who committed, not who understands the code. Do not use this to rank people.
