"""Profile and contractors config — persists to ~/.config/ip-reports/."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict


class ProfileMissingError(RuntimeError):
    """Raised when profile.json is missing. Message points to the wizard."""


def _config_dir() -> Path:
    override = os.environ.get("IP_REPORTS_CONFIG_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ip-reports"


def _profile_path() -> Path:
    return _config_dir() / "profile.json"


def _contractors_path() -> Path:
    return _config_dir() / "contractors.json"


@dataclass(frozen=True)
class Profile:
    fio: str
    inn: str
    ogrnip: str
    tax_system: str
    ruble_account: str
    bank_bic: str

    def __post_init__(self):
        if len(self.inn) not in (10, 12):
            raise ValueError(
                f"ИНН должен быть 10 или 12 цифр, получен: {self.inn!r}"
            )
        if self.tax_system not in ("PSN", "USN_income", "USN_income_minus_expense", "OSNO"):
            raise ValueError(f"Неизвестная система налогообложения: {self.tax_system!r}")


@dataclass(frozen=True)
class Contractor:
    name: str
    inn: str
    operation_type: str
    description_template: str


def save_profile(profile: Profile) -> None:
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(profile), ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile() -> Profile:
    path = _profile_path()
    if not path.exists():
        raise ProfileMissingError(
            f"Профиль не найден по пути {path}. Запусти wizard: "
            f"`python scripts/config.py wizard` или через SKILL.md."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return Profile(**data)


def save_contractor(contractor: Contractor) -> None:
    path = _contractors_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_contractors()
    existing[contractor.name] = contractor
    serialisable = {name: asdict(c) for name, c in existing.items()}
    path.write_text(json.dumps(serialisable, ensure_ascii=False, indent=2), encoding="utf-8")


def load_contractors() -> Dict[str, Contractor]:
    path = _contractors_path()
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {name: Contractor(**payload) for name, payload in raw.items()}


def run_wizard() -> Profile:
    """Interactive wizard — prompts for 6 fields, validates, saves."""
    print("=== ip-reports: профиль ИП ===")
    fio = input("ФИО полностью (как в Эльбе): ").strip()
    inn = input("ИНН (12 цифр для ИП): ").strip()
    ogrnip = input("ОГРНИП (15 цифр, можно пустым): ").strip()
    tax_system = input("Система налогообложения (PSN/USN_income/USN_income_minus_expense/OSNO): ").strip()
    ruble_account = input("Расчётный счёт РФ (20 цифр, можно пустым): ").strip() or "40802810123456789012"
    bank_bic = input("БИК банка (9 цифр, можно пустым): ").strip() or "044525000"
    profile = Profile(
        fio=fio, inn=inn, ogrnip=ogrnip, tax_system=tax_system,
        ruble_account=ruble_account, bank_bic=bank_bic,
    )
    save_profile(profile)
    print(f"Профиль сохранён: {_profile_path()}")
    return profile


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "wizard":
        run_wizard()
    else:
        print("Usage: python config.py wizard")
