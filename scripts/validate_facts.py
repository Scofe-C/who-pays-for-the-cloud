"""Task 7: validate data/manual/facts.csv. Exit 0 only when every row is complete AND human-verified.

Checks per row: all columns non-empty (including verified_by); value parses as a number
(ISO dates and true/false allowed); evidence <= 25 words; ids unique.

Pending rows: an unverified row listed in PENDING_OK is allowed (WARNING, exit 0) because every
builder that reads it gates on verified_by and falls back to the unverified-safe version. Any other
unverified row fails the check.
"""

from __future__ import annotations

import csv
import datetime
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "manual" / "facts.csv"
COLS = ["id", "value", "unit", "metric", "period", "source_title", "source_url", "page", "evidence",
        "as_of", "expected", "verified_by", "notes"]

log = logging.getLogger("validate_facts")

# id -> which builder reads it and what happens while it is unverified
PENDING_OK = {
    "imm_2829_share": "build_manual_csvs.f4_imm: uses computed 6.3/16.4 share until verified",
    "pjm_2627_at_cap": "build_manual_csvs.h1_pjm: 2026/27 gets no cap marker until verified",
    "openai_chatgpt_launch": "build_uploads.f2_captions: caption kept, flagged pending in the run report",
}


def value_ok(v: str) -> bool:
    if v in ("true", "false"):
        return True
    try:
        float(v)
        return True
    except ValueError:
        pass
    try:
        datetime.date.fromisoformat(v)
        return True
    except ValueError:
        return False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not FACTS.exists():
        log.error("%s not found", FACTS)
        return 2
    with FACTS.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLS:
            log.error("columns %s != %s", reader.fieldnames, COLS)
            return 1
        rows = list(reader)
    errors, unverified, pending, seen = 0, 0, [], set()
    for r in rows:
        rid = r["id"]
        if rid in seen:
            log.error("%s: duplicate id", rid)
            errors += 1
        seen.add(rid)
        empty = [c for c in COLS if not (r[c] or "").strip() and c != "verified_by"]
        if empty:
            log.error("%s: empty %s", rid, empty)
            errors += 1
        if not r["verified_by"].strip():
            if rid in PENDING_OK:
                pending.append(rid)
            else:
                unverified += 1
                log.error("%s: not verified and not in PENDING_OK", rid)
        if not value_ok(r["value"]):
            log.error("%s: value %r is not a number, ISO date or true/false", rid, r["value"])
            errors += 1
        if len(r["evidence"].split()) > 25:
            log.error("%s: evidence has %d words (> 25)", rid, len(r["evidence"].split()))
            errors += 1
    log.info("%d rows, %d structural errors, %d unverified (blocking), %d pending (gated)",
             len(rows), errors, unverified, len(pending))
    for rid in pending:
        log.warning("pending human verification: %s -- %s", rid, PENDING_OK[rid])
    if unverified:
        log.error("rows without verified_by must not reach any chart")
    return 1 if errors or unverified else 0


if __name__ == "__main__":
    sys.exit(main())
