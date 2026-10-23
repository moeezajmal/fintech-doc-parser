# Financial Document Parser

Extracts structured transactions from bank statement PDFs, stores them,
categorizes them, and answers natural-language questions about them.

**Status:** Phase 0 (setup) in progress. Synthetic test data and the core
schema are done. The parser comes next. Uses synthetic data only.

## Setup

```bash
git clone <your-repo-url>
cd fintech-doc-parser
python3 -m venv .venv
source .venv/bin/activate
pip install reportlab pydantic
```

## Generate the test data

```bash
python generate_statements.py --count 25 --seed 42
```

This writes to `data/synthetic/`:

- `pdfs/`: fake statement PDFs
- `truth/`: matching ground-truth JSON, one per PDF
- `manifest.json`: each file's layout, page count and transaction count

Options:

| Option | Default | Meaning |
|---|---|---|
| `--count N` | 25 | Number of statements. Statement i is identical regardless of N. |
| `--seed S` | 42 | Random seed. Same seed and code give identical output. |
| `--out DIR` | `data/synthetic` | Output folder. Use another folder for experiments. |

The committed set in `data/synthetic/` uses `--count 25 --seed 42`. For a
held-out test set, use a different seed and folder:

```bash
python generate_statements.py --count 100 --seed 99 --out data/heldout
```

## How the test data works

Data is generated first, then rendered to PDF. The generator builds the
transactions as validated Pydantic models, saves them as the ground-truth
JSON, and then draws the same data onto a PDF. Ground truth is therefore
exact by construction, with no hand labeling.

There are four layouts, chosen to stress a parser differently:

| Layout | Notable features |
|---|---|
| `classic` | Signed amount column, `MM/DD/YYYY` dates, balance column |
| `debit_credit` | Separate Debit and Credit columns, `05 Mar 2025` dates |
| `compact` | Negatives in parentheses, no balance column, no year on dates |
| `detailed` | Monospace font, ISO dates, `-$4.50` amounts, reference lines, distractor numbers |

Most statements run multiple pages with repeated table headers.

## Data conventions

- Money is `Decimal`, never `float`.
- Amounts are negative for money out and positive for money in.
- Each transaction records `source_page`, so values trace back to a page.
- If a statement doesn't show a running balance, the truth records `null`.

## Project layout

```
models.py                # Transaction and Statement schemas (Pydantic)
generate_statements.py   # synthetic statement generator
data/synthetic/          # generated PDFs, truth JSON, manifest
docs/                    # design notes
DECISIONS.md             # log of key choices and why
```

## Roadmap

- [x] Repo, README, DECISIONS.md
- [x] Pydantic schema
- [x] Synthetic statement generator (4 layouts, 25 statements)
- [ ] Parser: PDF text extraction, LLM structured output, OCR fallback
- [ ] Storage, categorization, natural-language queries
- [ ] Reconciliation, confidence scoring, evaluation
- [ ] UI, deployment, demo

## Data safety

Only synthetic data is committed. `data/real/` is git-ignored and must never
contain anything pushed to this repo.