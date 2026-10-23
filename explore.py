"""Explore what pdfplumber sees in our synthetic statements.

Usage:
  python explore.py                      # page 1 of one statement per layout
  python explore.py statement_003        # one statement, all modes
  python explore.py statement_003 --page 2 --mode words
  python explore.py --lines 40           # show more lines of text

Modes: text, tables, words, all (default)
"""
import argparse
import json
from pathlib import Path

import pdfplumber

DATA = Path("data/synthetic")


def show_text(page, max_lines):
    print("--- extract_text() ---")
    text = page.extract_text() or "(no text found)"
    lines = text.splitlines()
    for line in lines[:max_lines]:
        print(line)
    if len(lines) > max_lines:
        print(f"... ({len(lines) - max_lines} more lines)")


def show_tables(page, max_lines):
    print("--- extract_tables() ---")
    tables = page.extract_tables()
    print(f"tables found: {len(tables)}")
    for i, table in enumerate(tables):
        print(f"table {i}: {len(table)} rows")
        for row in table[:max_lines]:
            print("  ", row)


def show_words(page, max_lines):
    print("--- extract_words() (text, x0, top) ---")
    words = page.extract_words()
    print(f"words found: {len(words)}")
    for w in words[:max_lines]:
        print(f"  {w['text']!r:30} x0={w['x0']:.0f} top={w['top']:.0f}")


def explore(stem, layout, page_num, mode, max_lines):
    path = DATA / "pdfs" / f"{stem}.pdf"
    with pdfplumber.open(path) as pdf:
        print("=" * 70)
        print(f"{stem}  layout={layout}  pages={len(pdf.pages)}  showing page {page_num}")
        print("=" * 70)
        if not 1 <= page_num <= len(pdf.pages):
            print(f"This PDF has {len(pdf.pages)} pages; --page {page_num} is out of range.")
            return
        page = pdf.pages[page_num - 1]
        if mode in ("text", "all"):
            show_text(page, max_lines)
        if mode in ("tables", "all"):
            show_tables(page, max_lines)
        if mode in ("words", "all"):
            show_words(page, max_lines)
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stem", nargs="?", help="e.g. statement_003 (default: one per layout)")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--mode", choices=["text", "tables", "words", "all"], default="all")
    ap.add_argument("--lines", type=int, default=20)
    args = ap.parse_args()

    manifest = json.loads((DATA / "manifest.json").read_text())
    layouts = {m["id"]: m["layout"] for m in manifest}

    if args.stem:
        explore(args.stem, layouts.get(args.stem, "?"), args.page, args.mode, args.lines)
    else:
        seen = set()
        for m in manifest:
            if m["layout"] not in seen:
                seen.add(m["layout"])
                explore(m["id"], m["layout"], args.page, args.mode, args.lines)


if __name__ == "__main__":
    main()
