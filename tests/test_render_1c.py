from datetime import date
from pathlib import Path

from config import Profile, Contractor
from render_1c import render_elba_txt


FIXTURE = Path(__file__).parent / "fixtures" / "sample_extracted.json"


def _profile() -> Profile:
    return Profile(
        fio="ИП ТЕСТОВЫЙ",
        inn="000000000000",
        ogrnip="300000000000000",
        tax_system="PSN",
        ruble_account="40802810123456789012",
        bank_bic="044525000",
    )


def _contractor() -> Contractor:
    return Contractor(
        name="Blu Banyan Inc.",
        inn="9909999999",
        operation_type="Начисление вознаграждения по агентскому договору",
        description_template="поступление средств за {month} {year}",
    )


def test_render_produces_utf8_text(tmp_path):
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # For this test, use fixed rates so output is deterministic
    rates = {
        "2025-07-11": 77.9029,
        "2025-07-28": 79.5527,
        "2025-09-26": 83.6069,
    }
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data,
        profile=_profile(),
        contractors={"Blu Banyan Inc.": _contractor()},
        rates=rates,
        output_path=out,
    )
    # newline="" disables universal-newlines translation so \r\n is preserved on Windows
    with out.open(encoding="utf-8", newline="") as fh:
        text = fh.read()
    assert text.startswith("1CClientBankExchange\r\n")
    assert text.rstrip("\r\n").endswith("КонецФайла")
    assert "ВерсияФормата=1.03" in text
    assert "Кодировка=Windows" in text


def test_only_incoming_transactions_included(tmp_path):
    """Sample has 3 in + 1 out + 1 fee. File must contain only 3 documents."""
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rates = {
        "2025-07-11": 77.9029,
        "2025-07-28": 79.5527,
        "2025-09-26": 83.6069,
    }
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data, profile=_profile(),
        contractors={"Blu Banyan Inc.": _contractor()},
        rates=rates, output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert text.count("СекцияДокумент=Банковский ордер") == 3


def test_total_incoming_matches_sum_of_rub(tmp_path):
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rates = {
        "2025-07-11": 77.9029,
        "2025-07-28": 79.5527,
        "2025-09-26": 83.6069,
    }
    expected_total = (4000 * 77.9029) + (4000 * 79.5527) + (4000 * 83.6069)
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data, profile=_profile(),
        contractors={"Blu Banyan Inc.": _contractor()},
        rates=rates, output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert f"ВсегоПоступило={expected_total:.2f}" in text


def test_receiver_inn_and_name_use_profile(tmp_path):
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rates = {"2025-07-11": 77.9029, "2025-07-28": 79.5527, "2025-09-26": 83.6069}
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data, profile=_profile(),
        contractors={"Blu Banyan Inc.": _contractor()},
        rates=rates, output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert "ПолучательИНН=000000000000" in text
    assert "Получатель=ИП ТЕСТОВЫЙ" in text


def test_description_follows_month_logic(tmp_path):
    """Day ≤15 → prev month; >15 → current month."""
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rates = {"2025-07-11": 77.9029, "2025-07-28": 79.5527, "2025-09-26": 83.6069}
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data, profile=_profile(),
        contractors={"Blu Banyan Inc.": _contractor()},
        rates=rates, output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    # 11.07 → day 11 ≤ 15 → previous month = июнь 2025
    assert "НазначениеПлатежа=поступление средств за июнь 2025" in text
    # 28.07 → day 28 > 15 → current month = июль 2025
    assert "НазначениеПлатежа=поступление средств за июль 2025" in text
    # 26.09 → day 26 > 15 → current month = сентябрь 2025
    assert "НазначениеПлатежа=поступление средств за сентябрь 2025" in text


def test_payer_inn_uses_contractor_inn(tmp_path):
    """ПлательщикИНН comes from Contractor.inn so Эльба links the payment
    to the existing contractor card by ИНН match."""
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rates = {"2025-07-11": 77.9029, "2025-07-28": 79.5527, "2025-09-26": 83.6069}
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data, profile=_profile(),
        contractors={"Blu Banyan Inc.": _contractor()},
        rates=rates, output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert "ПлательщикИНН=9909999999" in text
    # And no leftover placeholder from the old hardcoded value
    assert "ПлательщикИНН=7700000001" not in text


def test_payer_inn_empty_when_contractor_unknown_or_inn_blank(tmp_path):
    """Эльба rejects made-up ИНН (checksum mismatch) and rejects 0000000000 too.
    If the contractor's ИНН is blank, we must emit an empty ПлательщикИНН= —
    Эльба then asks the user to manually pair once, remembering the mapping
    by name/account for subsequent imports."""
    import json
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rates = {"2025-07-11": 77.9029, "2025-07-28": 79.5527, "2025-09-26": 83.6069}
    out = tmp_path / "elba.txt"
    render_elba_txt(
        extracted=data, profile=_profile(),
        contractors={},  # empty — counterparty not registered
        rates=rates, output_path=out,
    )
    # Preserve CRLF on Windows
    with out.open(encoding="utf-8", newline="") as fh:
        text = fh.read()
    assert "ПлательщикИНН=\r\n" in text
    # the old '0000000000' fallback must not appear on the Плательщик side
    assert "ПлательщикИНН=0000000000" not in text
