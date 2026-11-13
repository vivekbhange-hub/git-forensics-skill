# Hotspots: demo-repo

- Window: all history
- Commits scanned: 51 (merge commits skipped)
- Files ranked: 46 (existing text files touched in the window, after excludes)
- Score: churn percentile x complexity percentile, 0 to 100; complexity is lines x (1 + mean indent level)

| # | File | Score | Commits | +Lines | -Lines | Authors | Lines | Max indent | Mean indent | Fix share | Why |
|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|
| 1 | `src/shop/orders.py` | 100.0 | 19 | 244 | 51 | 4 | 193 | 6.0 | 3.02 | 52.6% | changes often, large and deeply nested, many fixes, many authors |
| 2 | `billing/invoice.py` | 90.4 | 14 | 77 | 19 | 4 | 58 | 2.0 | 1.5 | 50.0% | changes often, large and deeply nested, many fixes, many authors |
| 3 | `src/shop/pricing.py` | 89.4 | 11 | 97 | 14 | 4 | 83 | 3.0 | 1.99 | 27.3% | changes often, large and deeply nested, many authors |
| 4 | `src/shop/legacy_sync.py` | 89.3 | 8 | 140 | 9 | 2 | 131 | 6.0 | 3.16 | 37.5% | changes often, large and deeply nested |
| 5 | `tests/test_orders.py` | 88.3 | 14 | 69 | 19 | 4 | 50 | 2.0 | 1.46 | 64.3% | changes often, large, many fixes, many authors |
| 6 | `docs/guide.md` | 77.5 | 7 | 41 | 0 | 3 | 41 | 1.0 | 1.0 | 0.0% | changes often, large |
| 7 | `web/templates/cart.html` | 73.6 | 5 | 43 | 3 | 3 | 40 | 2.0 | 1.5 | 20.0% | changes often, large and deeply nested |
| 8 | `src/shop/config.py` | 71.9 | 6 | 26 | 0 | 2 | 26 | 1.0 | 1.0 | 0.0% | changes often, large |
| 9 | `src/shop/helpers.py` | 67.3 | 4 | 25 | 4 | 3 | 21 | 2.0 | 1.48 | 50.0% | changes often, large, many fixes |
| 10 | `package.json` | 36.4 | 6 | 13 | 7 | 2 | 6 | 1.0 | 1.0 | 0.0% | changes often |

Fix share is the percentage of a file's commits whose subject mentions fix, bug, hotfix, revert or regression. It is a sanity check on the churn, not a measure of quality.
