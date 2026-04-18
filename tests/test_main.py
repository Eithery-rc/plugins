import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Profile, Contractor, save_profile, save_contractor
import main


FIXTURE = Path(__file__).parent / "fixtures" / "sample_extracted.json"

# Sample fixture: bank=Jusan, period=2025-07-01..2025-09-30 → slug '2025-Q3'
PREFIX = "Jusan-2025-Q3"


@pytest.fixture
def setup_config(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path / "config"))
    save_profile(Profile(
        fio="ИП ТЕСТОВЫЙ",
        inn="000000000000",
        ogrnip="300000000000000",
        tax_system="PSN",
        ruble_account="40802810123456789012",
        bank_bic="044525000",
    ))
    save_contractor(Contractor(
        name="Blu Banyan Inc.",
        inn="",
        operation_type="Начисление вознаграждения по агентскому договору",
        description_template="поступление средств за {month} {year}",
    ))


def _fake_rate(date_ddmmyyyy: str, currency: str = "USD") -> float:
    return {
        "11.07.2025": 77.9029,
        "28.07.2025": 79.5527,
        "15.08.2025": 79.8100,
        "31.08.2025": 80.5000,
        "26.09.2025": 83.6069,
    }[date_ddmmyyyy]


def test_main_produces_three_files(setup_config, tmp_path):
    src = tmp_path / "_extracted.json"
    shutil.copy(FIXTURE, src)
    out_dir = tmp_path / "out"

    with patch("main.get_usd_rate", side_effect=_fake_rate):
        main.run(input_path=src, out_dir=out_dir, cleanup_input=True)

    assert (out_dir / f"{PREFIX}-elba-import.txt").exists()
    assert (out_dir / f"{PREFIX}-journal.xlsx").exists()
    assert (out_dir / f"{PREFIX}-summary.md").exists()
    # cleanup removed input
    assert not src.exists()


def test_main_keeps_input_when_cleanup_false(setup_config, tmp_path):
    src = tmp_path / "_extracted.json"
    shutil.copy(FIXTURE, src)
    out_dir = tmp_path / "out"

    with patch("main.get_usd_rate", side_effect=_fake_rate):
        main.run(input_path=src, out_dir=out_dir, cleanup_input=False)

    assert src.exists()


def test_main_cli_args(setup_config, tmp_path, monkeypatch):
    """Verify argv parsing works."""
    src = tmp_path / "_extracted.json"
    shutil.copy(FIXTURE, src)
    out_dir = tmp_path / "out"

    monkeypatch.setattr("sys.argv", ["main.py", "--input", str(src), "--out", str(out_dir)])
    with patch("main.get_usd_rate", side_effect=_fake_rate):
        main.cli()

    assert (out_dir / f"{PREFIX}-elba-import.txt").exists()


def test_period_slug_quarter():
    assert main._period_slug({"start": "2025-07-01", "end": "2025-09-30"}) == "2025-Q3"
    assert main._period_slug({"start": "2025-01-01", "end": "2025-03-31"}) == "2025-Q1"
    assert main._period_slug({"start": "2025-04-01", "end": "2025-06-30"}) == "2025-Q2"
    assert main._period_slug({"start": "2025-10-01", "end": "2025-12-31"}) == "2025-Q4"


def test_period_slug_full_year():
    assert main._period_slug({"start": "2025-01-01", "end": "2025-12-31"}) == "2025"


def test_period_slug_full_month():
    assert main._period_slug({"start": "2025-07-01", "end": "2025-07-31"}) == "2025-07"
    assert main._period_slug({"start": "2025-02-01", "end": "2025-02-28"}) == "2025-02"


def test_period_slug_arbitrary_range_falls_back_to_dates():
    assert main._period_slug({"start": "2025-07-11", "end": "2025-09-26"}) == "2025-07-11_2025-09-26"
    # Cross-year range
    assert main._period_slug({"start": "2024-12-15", "end": "2025-01-14"}) == "2024-12-15_2025-01-14"
