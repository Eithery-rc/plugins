"""Render 1CClientBankExchange .txt file for Эльба import."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

from config import Profile, Contractor


MONTHS_RU = {
    1: "январь", 2: "февраль", 3: "март", 4: "апрель",
    5: "май", 6: "июнь", 7: "июль", 8: "август",
    9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
}


def _to_ddmmyyyy(iso_date: str) -> str:
    """Convert 'YYYY-MM-DD' → 'DD.MM.YYYY'."""
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return d.strftime("%d.%m.%Y")


def _payment_description(iso_date: str, template: str) -> str:
    """Build НазначениеПлатежа based on day-of-month logic."""
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    if d.day <= 15:
        target_month = d.month - 1 or 12
        target_year = d.year if d.month != 1 else d.year - 1
    else:
        target_month = d.month
        target_year = d.year
    return template.format(month=MONTHS_RU[target_month], year=target_year)


def render_elba_txt(
    extracted: dict,
    profile: Profile,
    contractors: Dict[str, Contractor],
    rates: Dict[str, float],
    output_path: Path,
) -> None:
    """Write a 1CClientBankExchange .txt file with incoming transactions only.

    Args:
        extracted: dict matching transactions.json schema
        profile: ИП profile
        contractors: name -> Contractor map
        rates: iso_date -> RUB rate for the currency used
        output_path: file to write (UTF-8, \\r\\n)
    """
    incoming = [t for t in extracted["transactions"] if t["direction"] == "in"]
    if not incoming:
        raise ValueError("No incoming transactions; nothing to render for Эльба.")

    # Convert USD → RUB using rates
    docs: List[dict] = []
    for tx in incoming:
        rate = rates[tx["date"]]
        amount_rub = round(tx["amount"] * rate, 2)
        contractor = contractors.get(tx["counterparty"]["name"], Contractor(
            name=tx["counterparty"]["name"],
            inn="",
            operation_type="",
            description_template="поступление средств за {month} {year}",
        ))
        docs.append({
            "date": _to_ddmmyyyy(tx["date"]),
            "amount_rub": amount_rub,
            "reference": tx["reference"],
            "counterparty_name": tx["counterparty"]["name"],
            "counterparty_inn": contractor.inn,  # empty string when unset → ПлательщикИНН= (empty); Эльба ok with it
            "description": _payment_description(tx["date"], contractor.description_template),
        })

    total = sum(d["amount_rub"] for d in docs)
    first_date = _to_ddmmyyyy(extracted["period"]["start"])
    last_date = _to_ddmmyyyy(extracted["period"]["end"])

    lines: List[str] = []
    A = lines.append

    # File header
    A("1CClientBankExchange")
    A("ВерсияФормата=1.03")
    A("Кодировка=Windows")
    A("Отправитель=ip-reports")
    A("Получатель=Эльба")
    A(f"ДатаСоздания={first_date}")
    A("ВремяСоздания=12:00:00")
    A(f"ДатаНачала={first_date}")
    A(f"ДатаКонца={last_date}")
    A(f"РасчСчет={profile.ruble_account}")
    A("Документ=Банковский ордер")

    # Account section
    A("СекцияРасчСчет")
    A(f"ДатаНачала={first_date}")
    A(f"ДатаКонца={last_date}")
    A(f"РасчСчет={profile.ruble_account}")
    A("НачальныйОстаток=0.00")
    A(f"ВсегоПоступило={total:.2f}")
    A("ВсегоСписано=0.00")
    A(f"КонечныйОстаток={total:.2f}")
    A("КонецРасчСчет")

    # Documents
    for d in docs:
        A("СекцияДокумент=Банковский ордер")
        A(f"Номер={d['reference']}")
        A(f"Дата={d['date']}")
        A(f"Сумма={d['amount_rub']:.2f}")
        # Плательщик (contractor)
        A(f"Плательщик={d['counterparty_name']}")
        A(f"Плательщик1={d['counterparty_name']}")
        A("ПлательщикСчет=40702810000000000001")
        A(f"ПлательщикИНН={d['counterparty_inn']}")
        A("ПлательщикБИК=044525000")
        A("ПлательщикБанк1=Payer Correspondent Bank")
        A("ПлательщикКорсчет=30101810000000000001")
        # Получатель (us)
        A(f"Получатель={profile.fio}")
        A(f"Получатель1={profile.fio}")
        A(f"ПолучательСчет={profile.ruble_account}")
        A(f"ПолучательИНН={profile.inn}")
        A(f"ПолучательБИК={profile.bank_bic}")
        A("ПолучательБанк1=Placeholder Bank")
        A("ПолучательКорсчет=30101810000000000001")
        # Payment details
        A("ВидОплаты=01")
        A("Очередность=5")
        A(f"НазначениеПлатежа={d['description']}")
        A(f"ДатаПоступило={d['date']}")
        A("КонецДокумента")

    A("КонецФайла")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\r\n".join(lines) + "\r\n"
    output_path.write_bytes(content.encode("utf-8"))
