"""Orchestrator: extracted.json -> (elba-import.txt, journal.xlsx, summary.md)."""
from __future__ import annotations

import argparse
import calendar
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from config import load_profile, load_contractors
from cbr_rates import get_usd_rate
from render_1c import render_elba_txt
from render_xlsx import render_journal_xlsx
from render_summary import render_summary_md


def _collect_rates(extracted: dict) -> Dict[str, float]:
    """Fetch CBR rate for each unique date used by incoming transactions."""
    needed_iso = {t["date"] for t in extracted["transactions"] if t["direction"] == "in"}
    rates: Dict[str, float] = {}
    for iso_date in sorted(needed_iso):
        dd = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        rates[iso_date] = get_usd_rate(dd, extracted["account"]["currency"])
    return rates


def _period_slug(period: dict) -> str:
    """Turn {start,end} into a short human-readable slug.

    - Full calendar year         → '2025'
    - Full calendar quarter      → '2025-Q3'
    - Full calendar month        → '2025-07'
    - Anything else              → '2025-07-11_2025-09-26'
    """
    start = datetime.strptime(period["start"], "%Y-%m-%d").date()
    end = datetime.strptime(period["end"], "%Y-%m-%d").date()

    if start.year == end.year:
        if (start.month, start.day) == (1, 1) and (end.month, end.day) == (12, 31):
            return f"{start.year}"

        quarter_starts = {(1, 1): 1, (4, 1): 2, (7, 1): 3, (10, 1): 4}
        quarter_ends = {(3, 31): 1, (6, 30): 2, (9, 30): 3, (12, 31): 4}
        q_from_start = quarter_starts.get((start.month, start.day))
        q_from_end = quarter_ends.get((end.month, end.day))
        if q_from_start is not None and q_from_start == q_from_end:
            return f"{start.year}-Q{q_from_start}"

        if (
            start.month == end.month
            and start.day == 1
            and end.day == calendar.monthrange(end.year, end.month)[1]
        ):
            return f"{start.year}-{start.month:02d}"

    return f"{period['start']}_{period['end']}"


def _output_paths(out_dir: Path, extracted: dict) -> Dict[str, Path]:
    """Build meaningful filenames: '{Bank}-{period-slug}-{artifact}.{ext}'."""
    prefix = f"{extracted['bank']}-{_period_slug(extracted['period'])}"
    return {
        "elba": out_dir / f"{prefix}-elba-import.txt",
        "journal": out_dir / f"{prefix}-journal.xlsx",
        "summary": out_dir / f"{prefix}-summary.md",
    }


def run(input_path: Path, out_dir: Path, cleanup_input: bool = True) -> None:
    """Render 3 artifacts from extracted JSON into out_dir."""
    extracted = json.loads(input_path.read_text(encoding="utf-8"))
    profile = load_profile()
    contractors = load_contractors()

    rates = _collect_rates(extracted)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = _output_paths(out_dir, extracted)

    render_elba_txt(
        extracted=extracted, profile=profile, contractors=contractors,
        rates=rates, output_path=paths["elba"],
    )
    render_journal_xlsx(
        extracted=extracted, profile=profile, contractors=contractors,
        rates=rates, output_path=paths["journal"],
    )

    incoming_count = sum(1 for t in extracted["transactions"] if t["direction"] == "in")
    total_rub = sum(t["amount"] * rates[t["date"]] for t in extracted["transactions"] if t["direction"] == "in")
    render_summary_md(
        extracted=extracted,
        total_rub=round(total_rub, 2),
        incoming_count=incoming_count,
        output_path=paths["summary"],
    )

    if cleanup_input:
        input_path.unlink(missing_ok=True)


def cli() -> None:
    parser = argparse.ArgumentParser(description="ip-reports orchestrator")
    parser.add_argument("--input", required=True, help="Path to extracted.json")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--keep-input", action="store_true", help="Do not delete input JSON after processing")
    args = parser.parse_args()
    run(Path(args.input), Path(args.out), cleanup_input=not args.keep_input)


if __name__ == "__main__":
    cli()
