# Temporal coupling: demo-repo

- Window: all history
- Commits counted: 49 (25 touched only one tracked file); skipped 2 bulk commits touching more than 30 files
- Pairs shown: shared commits >= 4, confidence >= 0.6 in at least one direction

| # | File A | File B | Shared | Support | A->B | B->A | Cross-module | Reference | Flags |
|--:|---|---|--:|--:|--:|--:|---|---|---|
| 1 | `src/shop/orders.py` | `tests/test_orders.py` | 14 | 0.286 | 0.74 | 1.0 | yes | mentioned | test and code |
| 2 | `billing/invoice.py` | `src/shop/orders.py` | 12 | 0.245 | 0.86 | 0.63 | yes | none seen | hidden dependency? |
| 3 | `billing/invoice.py` | `tests/test_orders.py` | 11 | 0.224 | 0.79 | 0.79 | yes | none seen | hidden dependency? |
| 4 | `src/shop/orders.py` | `src/shop/pricing.py` | 8 | 0.163 | 0.42 | 0.73 | no | mentioned | - |
| 5 | `docs/guide.md` | `src/shop/config.py` | 6 | 0.122 | 0.86 | 1.0 | yes | none seen | hidden dependency? |
| 6 | `src/shop/orders.py` | `web/templates/cart.html` | 4 | 0.082 | 0.21 | 0.8 | yes | none seen | hidden dependency? |
| 7 | `src/shop/pricing.py` | `web/templates/cart.html` | 4 | 0.082 | 0.36 | 0.8 | yes | none seen | hidden dependency? |

## Clusters

1. `billing/invoice.py`, `src/shop/orders.py`, `src/shop/pricing.py`, `tests/test_orders.py`, `web/templates/cart.html`
2. `docs/guide.md`, `src/shop/config.py`

Reference means the file name (without extension) of one file appears as a word in the other. It is a cheap text check: generic names, dynamic loading and config files fool it.
