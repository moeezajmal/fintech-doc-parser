"""Generate synthetic bank statements: PDFs plus exact ground-truth JSON.

Data is generated FIRST (as Pydantic models), then rendered to PDF in one of
several layouts. Ground truth is therefore exact by construction.

Usage:  python generate_statements.py --count 25 --seed 42
"""
import argparse
import calendar
import datetime as dt
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from models import Statement, Transaction

CENT = Decimal("0.01")
PAGE_W, PAGE_H = letter
MARGIN = 50
BOTTOM = 70


def money(cents: int) -> Decimal:
    """Build exact money from integer cents. Never from floats."""
    return (Decimal(cents) / 100).quantize(CENT)


# ---------------------------------------------------------------- fake data
SPEND = [  # (merchant, min_cents, max_cents)
    ("STARBUCKS", 350, 1100), ("WHOLE FOODS MARKET", 2500, 14000),
    ("SHELL OIL", 3000, 7500), ("NETFLIX.COM", 1549, 1549),
    ("AMAZON MKTPLACE", 800, 12000), ("UBER TRIP", 900, 3500),
    ("CHIPOTLE", 1000, 2200), ("TARGET", 1500, 9000),
    ("COMCAST CABLE", 8999, 8999), ("CVS PHARMACY", 500, 4000),
    ("SPOTIFY USA", 1099, 1099), ("DOORDASH", 1800, 5500),
    ("TRADER JOES", 2000, 9000), ("PG&E UTILITIES", 6000, 15000),
    ("ATM WITHDRAWAL", 2000, 20000),
]
BANKS = ["First Fake Bank", "Harbor Trust", "Pinecrest Credit Union",
         "Northwind Savings", "Maple & Oak Bank"]


def generate_transactions(rng, start, end):
    """Return (opening_balance, [(date, description, amount, balance), ...])."""
    span = (end - start).days
    rows = []  # (date, description, amount)

    for day in (start + dt.timedelta(days=span // 2), end - dt.timedelta(days=1)):
        rows.append((day, "PAYROLL DEPOSIT ACME CORP", money(rng.randint(180000, 260000))))
    rows.append((start + dt.timedelta(days=2), "RENT PAYMENT", -money(rng.randint(120000, 180000))))
    if rng.random() < 0.5:
        rows.append((start + dt.timedelta(days=rng.randint(3, span)),
                     "ZELLE PAYMENT FROM J SMITH", money(rng.randint(2000, 20000))))

    for _ in range(rng.randint(18, 75)):
        name, lo, hi = rng.choice(SPEND)
        suffix = f" #{rng.randint(100, 9999)}" if rng.random() < 0.6 else ""
        day = start + dt.timedelta(days=rng.randint(0, span))
        rows.append((day, name + suffix, -money(rng.randint(lo, hi))))

    rows.sort(key=lambda r: r[0])  # stable: same-day order is preserved
    opening = money(rng.randint(500000, 900000))
    balance, out = opening, []
    for day, desc, amt in rows:
        balance += amt
        out.append((day, desc, amt, balance))
    return opening, out


# ------------------------------------------------------------------ layouts
def fmt(d: Decimal) -> str:
    return f"{abs(d):,.2f}"


@dataclass
class Layout:
    name: str
    font: str
    cols: list            # (header, x, align) align = "l" or "r"
    row_h: int
    shows_balance: bool
    date_fmt: str
    cells: callable       # (txn_tuple, layout) -> list[str]
    ref_line: bool = False
    year_in_header: bool = False
    notice: bool = False


def cells_classic(t, L):
    d, desc, amt, bal = t
    sign = "-" if amt < 0 else ""
    return [d.strftime(L.date_fmt), desc, f"{sign}{fmt(amt)}", fmt(bal) if bal >= 0 else f"-{fmt(bal)}"]


def cells_debit_credit(t, L):
    d, desc, amt, bal = t
    return [d.strftime(L.date_fmt), desc, fmt(amt) if amt < 0 else "",
            fmt(amt) if amt > 0 else "", fmt(bal)]


def cells_compact(t, L):
    d, desc, amt, _ = t
    return [d.strftime(L.date_fmt), desc, f"({fmt(amt)})" if amt < 0 else fmt(amt)]


def cells_detailed(t, L):
    d, desc, amt, bal = t
    sign = "-" if amt < 0 else ""
    return [d.strftime(L.date_fmt), desc, f"{sign}${fmt(amt)}", f"${fmt(bal)}"]


LAYOUTS = [
    Layout("classic", "Helvetica",
           [("Date", 50, "l"), ("Description", 130, "l"), ("Amount", 450, "r"), ("Balance", 562, "r")],
           16, True, "%m/%d/%Y", cells_classic),
    Layout("debit_credit", "Helvetica",
           [("Date", 50, "l"), ("Description", 125, "l"), ("Debit", 395, "r"),
            ("Credit", 470, "r"), ("Balance", 562, "r")],
           16, True, "%d %b %Y", cells_debit_credit),
    Layout("compact", "Helvetica",
           [("Posted", 50, "l"), ("Details", 105, "l"), ("Amount", 562, "r")],
           14, False, "%d %b", cells_compact, year_in_header=True),
    Layout("detailed", "Courier",
           [("DATE", 50, "l"), ("DESCRIPTION", 125, "l"), ("AMOUNT", 460, "r"), ("BALANCE", 562, "r")],
           30, True, "%Y-%m-%d", cells_detailed, ref_line=True, notice=True),
]


# ---------------------------------------------------------------- rendering
def draw_cell(c, text, x, y, align):
    if align == "r":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def table_header(c, L, y):
    c.setFont(L.font + "-Bold" if L.font == "Helvetica" else "Courier-Bold", 9)
    for header, x, align in L.cols:
        draw_cell(c, header, x, y, align)
    c.line(MARGIN, y - 4, PAGE_W - MARGIN, y - 4)
    c.setFont(L.font, 9)
    return y - 20


def footer(c, bank, page):
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN, 40, f"{bank}  |  Member FDIC (fictional, synthetic data)")
    c.drawRightString(PAGE_W - MARGIN, 40, f"Page {page}")


def first_page_header(c, L, meta):
    y = PAGE_H - MARGIN
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN, y, meta["bank_name"])
    c.setFont("Helvetica", 10)
    y -= 22
    c.drawString(MARGIN, y, f"Account ending in {meta['last4']}")
    y -= 14
    ps, pe = meta["start"], meta["end"]
    c.drawString(MARGIN, y, f"Statement period: {ps:%B %d, %Y} to {pe:%B %d, %Y}")
    y -= 26
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, y, "Account summary")
    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(MARGIN, y, "Opening balance")
    c.drawRightString(300, y, f"${fmt(meta['opening'])}")
    y -= 14
    c.drawString(MARGIN, y, "Closing balance")
    c.drawRightString(300, y, f"${fmt(meta['closing'])}")
    y -= 24
    if L.notice:  # distractor text with numbers, on purpose
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(MARGIN, y, "Notice: Your savings rate changes to 4.25% APY on the 1st. "
                                "Overdraft fee is $35.00 per item.")
        y -= 22
    if L.year_in_header:
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN, y, f"All dates are in {pe.year}.")
        y -= 16
    return table_header(c, L, y)


def continued_header(c, L, meta):
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, PAGE_H - MARGIN, f"{meta['bank_name']} - Account ending {meta['last4']} (continued)")
    return table_header(c, L, PAGE_H - MARGIN - 28)


def render(path, L, meta, txns):
    """Draw the PDF. Returns the page number each transaction landed on."""
    c = canvas.Canvas(str(path), pagesize=letter)
    page, pages = 1, []
    y = first_page_header(c, L, meta)
    for t in txns:
        if y - L.row_h < BOTTOM:
            footer(c, meta["bank_name"], page)
            c.showPage()
            page += 1
            y = continued_header(c, L, meta)
        c.setFont(L.font, 9)
        for (_, x, align), text in zip(L.cols, L.cells(t, L)):
            draw_cell(c, text, x, y, align)
        if L.ref_line:
            c.setFont(L.font, 7)
            c.drawString(L.cols[1][1], y - 10, f"Ref {random.Random(str(t)).randint(10**9, 10**10 - 1)} POS PURCHASE")
        pages.append(page)
        y -= L.row_h
    footer(c, meta["bank_name"], page)
    c.save()
    return pages


# --------------------------------------------------------------------- main
def build_one(index, seed, out_dir):
    rng = random.Random(f"{seed}-{index}")
    L = LAYOUTS[index % len(LAYOUTS)]
    year, month = 2025, rng.randint(1, 12)
    start = dt.date(year, month, 1)
    end = dt.date(year, month, calendar.monthrange(year, month)[1])

    opening, rows = generate_transactions(rng, start, end)
    closing = rows[-1][3]
    meta = dict(bank_name=rng.choice(BANKS), last4=str(rng.randint(1000, 9999)),
                start=start, end=end, opening=opening, closing=closing)

    stem = f"statement_{index + 1:03d}"
    pages = render(out_dir / "pdfs" / f"{stem}.pdf", L, meta, rows)

    statement = Statement(  # validates, including reconciliation
        bank_name=meta["bank_name"], account_last4=meta["last4"],
        period_start=start, period_end=end,
        opening_balance=opening, closing_balance=closing,
        transactions=[
            Transaction(date=d, description=desc, amount=amt,
                        balance=bal if L.shows_balance else None, source_page=p)
            for (d, desc, amt, bal), p in zip(rows, pages)
        ],
    )
    (out_dir / "truth" / f"{stem}.json").write_text(statement.model_dump_json(indent=2))
    return {"id": stem, "layout": L.name, "transactions": len(rows), "pages": max(pages)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=25)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("data/synthetic"))
    args = ap.parse_args()

    (args.out / "pdfs").mkdir(parents=True, exist_ok=True)
    (args.out / "truth").mkdir(parents=True, exist_ok=True)
    manifest = [build_one(i, args.seed, args.out) for i in range(args.count)]
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    multi = sum(1 for m in manifest if m["pages"] > 1)
    print(f"Wrote {len(manifest)} statements to {args.out} ({multi} multi-page)")


if __name__ == "__main__":
    main()
