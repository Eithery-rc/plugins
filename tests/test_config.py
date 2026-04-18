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
    complete_inn10,
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


def test_complete_inn10_computes_valid_checksum():
    # Prefix 990900000 → control digit 4 (verified against ФНС algorithm)
    assert complete_inn10("990900000") == "9909000004"
    # Different prefix produces different checksum
    assert complete_inn10("990900001") == "9909000011"
    # Checksum is deterministic and idempotent with the same prefix
    assert complete_inn10("123456789") == complete_inn10("123456789")


def test_complete_inn10_rejects_invalid_prefix():
    with pytest.raises(ValueError):
        complete_inn10("12345678")  # 8 digits
    with pytest.raises(ValueError):
        complete_inn10("12345678x")  # has non-digit
