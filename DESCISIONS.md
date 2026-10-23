# Decisions

A running log of key choices and why I made them.

## 2026-10-13: Python and FastAPI
- Python 3.x with FastAPI for the API layer.
- Why: (your own words, one or two sentences)

## 20206-10-23: Money is Decimal, built from strings or integer cents
- All money fields use `Decimal`. The generator creates amounts from integer
  cents, never from floats.
- Why: floats can't represent values like 0.1 exactly, which would break the
  reconciliation check (opening + transactions = closing) on correct data.

## 20206-10-23: Sign convention for amounts
- Negative = money out, positive = money in. One convention in the schema.
- Why: statements show amounts in different ways (signed, debit/credit
  columns, parentheses). The parser's job is to convert every layout into
  this single form.

## 20206-10-23: Generate data first, then render to PDF
- The generator builds validated models, saves them as ground truth, then
  draws the PDF from the same data.
- Why: ground truth is exact by construction, with no manual labeling and no
  real financial data needed.

## 20206-10-23: Record source_page at render time
- `source_page` is captured as each row is drawn, not computed afterwards.
- Why: it makes the audit trail (value to source page) exact, which the
  fintech checklist requires.

## 20206-10-23: Seeded randomness, with a held-out set
- Each statement uses its own `random.Random(f"{seed}-{index}")`. The
  committed set is `--count 25 --seed 42`. Experiments go to other folders.
- Why: reproducible evals, so a change in accuracy means the parser changed,
  not the data. A different seed gives a held-out set to check for
  overfitting.

## 20206-10-23: Four layouts, with a manifest recording each
- Layouts: classic, debit_credit, compact, detailed. `manifest.json` maps each
  file to its layout.
- Why: layouts differ on purpose (date formats, debit/credit columns,
  parentheses, missing balance, distractor text) to stress the parser. The
  manifest allows per-layout accuracy reporting in Phase 3.

## 20206-10-23: Truth records only what is on the page
- If a layout has no balance column, `balance` is `null` in the truth.
- Why: ground truth should match what a parser can actually see, otherwise
  it would be penalized for missing information that isn't there.

## 20206-10-23: Strict schema, and reject vs flag
- Models use `extra="forbid"`. `Statement` raises an error if it doesn't
  reconcile.
- Why: forbidding extra fields catches an LLM inventing or misspelling
  fields. The hard error is right for the generator (it catches bugs). The
  parser should not crash on a mismatch; in Phase 3 it will flag the
  statement for human review instead.

## 20206-10-23: Synthetic data only in the repo
- `data/real/` is git-ignored. Only generated data is committed.
- Why: no real PII in a public repo, per the fintech checklist.