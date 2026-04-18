import json
from unittest.mock import patch, MagicMock

import pytest

from cbr_rates import get_usd_rate, _parse_daily_xml, RateCache


SAMPLE_XML = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="11.07.2025" name="Foreign Currency Market">
  <Valute ID="R01235">
    <NumCode>840</NumCode>
    <CharCode>USD</CharCode>
    <Nominal>1</Nominal>
    <Name>Доллар США</Name>
    <Value>77,9029</Value>
  </Valute>
  <Valute ID="R01239">
    <NumCode>978</NumCode>
    <CharCode>EUR</CharCode>
    <Nominal>1</Nominal>
    <Name>Евро</Name>
    <Value>91,2345</Value>
  </Valute>
</ValCurs>
"""


def test_parse_daily_xml_extracts_usd_rate():
    rate = _parse_daily_xml(SAMPLE_XML, "USD")
    assert rate == 77.9029


def test_parse_daily_xml_handles_comma_decimal():
    rate = _parse_daily_xml(SAMPLE_XML, "EUR")
    assert rate == 91.2345


def test_parse_daily_xml_unknown_currency_raises():
    with pytest.raises(ValueError):
        _parse_daily_xml(SAMPLE_XML, "ZZZ")


def test_get_usd_rate_fetches_and_caches(tmp_path, monkeypatch):
    cache_path = tmp_path / "rates_cache.json"
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))

    fake_response = MagicMock()
    fake_response.content = SAMPLE_XML.encode("windows-1251")
    fake_response.raise_for_status = MagicMock()

    with patch("cbr_rates.requests.get", return_value=fake_response) as mock_get:
        rate1 = get_usd_rate("11.07.2025")
        assert rate1 == 77.9029
        assert mock_get.call_count == 1

        # second call — should hit cache, no HTTP
        rate2 = get_usd_rate("11.07.2025")
        assert rate2 == 77.9029
        assert mock_get.call_count == 1  # no extra call


def test_cache_persists_to_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("IP_REPORTS_CONFIG_DIR", str(tmp_path))
    cache = RateCache()
    cache.set("USD", "11.07.2025", 77.9029)
    cache.save()

    cache2 = RateCache()
    cache2.load()
    assert cache2.get("USD", "11.07.2025") == 77.9029
