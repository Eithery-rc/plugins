"""CBR rate fetcher + on-disk cache."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

import requests

from config import _config_dir


CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"


class RateCache:
    """Simple {currency: {date: rate}} cache on disk."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, float]] = {}
        self._path: Path = _config_dir() / "rates_cache.json"
        if self._path.exists():
            self.load()

    def load(self) -> None:
        self._data = json.loads(self._path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, currency: str, date: str) -> Optional[float]:
        return self._data.get(currency, {}).get(date)

    def set(self, currency: str, date: str, rate: float) -> None:
        self._data.setdefault(currency, {})[date] = rate


def _parse_daily_xml(xml_text: str, currency: str) -> float:
    root = ET.fromstring(xml_text)
    for valute in root.findall("Valute"):
        code = valute.findtext("CharCode")
        if code == currency:
            nominal = int(valute.findtext("Nominal") or "1")
            value_str = (valute.findtext("Value") or "").replace(",", ".")
            return float(value_str) / nominal
    raise ValueError(f"Currency {currency!r} not found in CBR XML")


def get_usd_rate(date_ddmmyyyy: str, currency: str = "USD") -> float:
    """
    Fetch RUB rate for the given currency on the given date.
    date_ddmmyyyy: 'DD.MM.YYYY' — format CBR expects.
    Returns rate as float. Caches results on disk.
    """
    cache = RateCache()
    cached = cache.get(currency, date_ddmmyyyy)
    if cached is not None:
        return cached

    response = requests.get(
        CBR_URL,
        params={"date_req": date_ddmmyyyy},
        timeout=10,
    )
    response.raise_for_status()
    # CBR returns windows-1251
    xml_text = response.content.decode("windows-1251")
    rate = _parse_daily_xml(xml_text, currency)
    cache.set(currency, date_ddmmyyyy, rate)
    cache.save()
    return rate
