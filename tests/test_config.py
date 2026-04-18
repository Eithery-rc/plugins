import json
import os
import pytest
from pathlib import Path

from config import (
    Profile,
    Contractor,
    load_profile,
    save_profile,
    load_contractors,
    save_contractor,
    ProfileMissingError,
)


def test_save_and_load_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))
    profile = Profile(
        fio="ИП ТЕСТОВЫЙ",
        inn="000000000000",
        ogrnip="300000000000000",
        tax_system="PSN",
        ruble_account="40802810123456789012",
        bank_bic="044525000",
    )
    save_profile(profile)
    loaded = load_profile()
    assert loaded == profile


def test_load_profile_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))
    with pytest.raises(ProfileMissingError) as excinfo:
        load_profile()
    assert "wizard" in str(excinfo.value).lower() or "визард" in str(excinfo.value).lower()


def test_save_and_load_contractors(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))
    contractor = Contractor(
        name="Blu Banyan Inc.",
        inn="",
        operation_type="Начисление вознаграждения по агентскому договору",
        description_template="поступление средств за {month} {year}",
    )
    save_contractor(contractor)
    contractors = load_contractors()
    assert "Blu Banyan Inc." in contractors
    assert contractors["Blu Banyan Inc."] == contractor


def test_load_contractors_empty_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))
    assert load_contractors() == {}


def test_profile_validation_rejects_short_inn(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        Profile(
            fio="X",
            inn="123",
            ogrnip="",
            tax_system="PSN",
            ruble_account="",
            bank_bic="",
        )
