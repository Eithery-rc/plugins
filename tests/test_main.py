import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Profile, Contractor, save_profile, save_contractor
import main


FIXTURE = Path(__file__).parent / "fixtures" / "sample_extracted.json"


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

    assert (out_dir / "elba_import.txt").exists()
    assert (out_dir / "journal.xlsx").exists()
    assert (out_dir / "summary.md").exists()
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

    assert (out_dir / "elba_import.txt").exists()
