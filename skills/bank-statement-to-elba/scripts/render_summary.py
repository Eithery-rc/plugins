"""Generate summary.md — a human-readable report for Claude and the user."""
from __future__ import annotations

from collections import Counter
from pathlib import Path


def render_summary_md(
    extracted: dict,
    total_rub: float,
    incoming_count: int,
    output_path: Path,
    include_elba_steps: bool = True,
) -> None:
    """Write summary.md describing what was done and what the user must do next."""
    bank = extracted["bank"]
    period = f'{extracted["period"]["start"]} — {extracted["period"]["end"]}'
    account = extracted["account"]["number"]

    # Count VO codes
    vo_counts = Counter(t["vo_code"] for t in extracted["transactions"])
    vo_lines = []
    for code, count in sorted(vo_counts.items()):
        total_amount = sum(
            t["amount"] for t in extracted["transactions"] if t["vo_code"] == code
        )
        vo_lines.append(f"- **{code}** — {count} опер., сумма: {total_amount:.2f} {extracted['account']['currency']}")
    vo_block = "\n".join(vo_lines) if vo_lines else "(нет операций)"

    generated_files = [
        "- `*-journal.xlsx` — локальный реестр (Журнал + ВЭД + Сводка)",
        "- `*-summary.md` — этот файл",
    ]
    if include_elba_steps:
        generated_files.insert(0, "- `*-elba-import.txt` — импорт в Эльбу")
    generated_block = "\n".join(generated_files)

    elba_section = ""
    if include_elba_steps:
        elba_section = """

## Шаги в Эльбе после импорта

1. **Загрузи** файл `*-elba-import.txt`: «Деньги → Загрузить файл из банка».
2. **Удали старые ручные записи** за этот период (если были) — Эльба не дедуплицирует.
3. **Исправь тип операции массово** (bulk-edit):
   - Поставь галку **«Тип операции»** над колонкой.
   - Выдели все импортированные строки.
   - Смени тип на **«Начисление вознаграждения по агентскому договору»**.
4. Проверь колонку «В налогах, ₽» — суммы должны совпадать с Сводкой.

Тип операции из файла задать нельзя — Эльба всегда ставит дефолт. Bulk-edit делается один раз на весь импортированный период. Привязка к карточке контрагента работает только при совпадении `ПлательщикИНН` — placeholder-ИНН в карточке Эльбы должен совпадать с `Contractor.inn` в `~/.config/ip-reports/contractors.json`."""

    text = f"""# Отчёт по обработке выписки

**Источник:** {extracted['source_pdf']}
**Банк:** {bank}
**Счёт:** {account}
**Период:** {period}

## Результат

- Извлечено транзакций: {len(extracted['transactions'])}
- Зачислений (доход): {incoming_count}
- Итого ₽ по курсу ЦБ: **{total_rub:.2f}**

## Разбивка по кодам ВО (181-И)

{vo_block}

Коды:
- **20200** — Зачисление от нерезидента за услуги/работы/ИС
- **61100** — Перевод резидентом на свой счёт за пределами РФ
- **80150** — Комиссии банка-нерезидента

Если видишь другие коды — их нужно подтвердить по приложению 1 к 181-И.

## Сгенерированные файлы (в этой же папке)

{generated_block}

Имена начинаются с `{{Банк}}-{{Период}}-...` (например, `TBC-2025-Q3-*`).{elba_section}

## Отчёт для банка/налоговой по ВЭД

Открой лист **«ВЭД»** в `*-journal.xlsx` — там готовые агрегаты по кодам 181-И для формы валютного контроля.
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
