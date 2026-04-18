"""Golden-file regression test — verifies our output matches a known-good file."""
import json
from pathlib import Path

from config import Profile, Contractor
from render_1c import render_elba_txt


def test_golden_elba_txt_unchanged(tmp_path):
    profile = Profile(
        fio="ИП ТЕСТОВЫЙ", inn="000000000000", ogrnip="300000000000000",
        tax_system="PSN", ruble_account="40802810123456789012", bank_bic="044525000",
    )
    contractor = Contractor(
        name="Blu Banyan Inc.", inn="",
        operation_type="Начисление вознаграждения по агентскому договору",
        description_template="поступление средств за {month} {year}",
    )
    data = json.loads(
        (Path(__file__).parent / "fixtures" / "sample_extracted.json").read_text(encoding="utf-8")
    )
    rates = {"2025-07-11": 77.9029, "2025-07-28": 79.5527, "2025-09-26": 83.6069}

    out = tmp_path / "produced.txt"
    render_elba_txt(data, profile, {"Blu Banyan Inc.": contractor}, rates, out)

    # Read both with newline="" to preserve \r\n on Windows
    with out.open(encoding="utf-8", newline="") as fh:
        produced = fh.read()
    with (Path(__file__).parent / "golden" / "sample_elba_import.txt").open(encoding="utf-8", newline="") as fh:
        golden = fh.read()
    assert produced == golden, "Output drifted from golden file. If change is intentional, regenerate golden."
