"""Orchestrator: extracted.json -> (elba_import.txt, journal.xlsx, summary.md)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

from config import load_profile, load_contractors
from cbr_rates import get_usd_rate
from render_1c import render_elba_txt, _to_ddmmyyyy
from render_xlsx import render_journal_xlsx
from render_summary import render_summary_md


def _collect_rates(extracted: dict) -> Dict[str, float]:
    """Fetch CBR rate for each unique date used by transactions (incoming only — rates used for RUB conversion)."""
    needed_iso = {t["date"] for t in extracted["transactions"] if t["direction"] == "in"}
    rates: Dict[str, float] = {}
    for iso_date in sorted(needed_iso):
        dd = datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")
        rates[iso_date] = get_usd_rate(dd, extracted["account"]["currency"])
    return rates


def run(input_path: Path, out_dir: Path, cleanup_input: bool = True) -> None:
    """Render 3 artifacts from extracted JSON into out_dir."""
    extracted = json.loads(input_path.read_text(encoding="utf-8"))
    profile = load_profile()
    contractors = load_contractors()

    rates = _collect_rates(extracted)

    out_dir.mkdir(parents=True, exist_ok=True)

    render_elba_txt(
        extracted=extracted, profile=profile, contractors=contractors,
        rates=rates, output_path=out_dir / "elba_import.txt",
    )
    render_journal_xlsx(
        extracted=extracted, profile=profile, contractors=contractors,
        rates=rates, output_path=out_dir / "journal.xlsx",
    )

    incoming_count = sum(1 for t in extracted["transactions"] if t["direction"] == "in")
    total_rub = sum(t["amount"] * rates[t["date"]] for t in extracted["transactions"] if t["direction"] == "in")
    render_summary_md(
        extracted=extracted,
        total_rub=round(total_rub, 2),
        incoming_count=incoming_count,
        output_path=out_dir / "summary.md",
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
