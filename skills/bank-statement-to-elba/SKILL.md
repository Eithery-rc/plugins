---
name: bank-statement-to-elba
description: Use when user asks to process a foreign-bank PDF statement (Jusan KZ, TBC GE, or similar) into an Эльба-importable .txt file, a local КУДиР Excel journal, and a ВЭД 181-И report. Trigger phrases include "обработай выписку", "выписка в Эльбу", "1C из выписки", "КУДиР из PDF", "ВЭД по счёту", "statement to Elba".
---

# Bank statement → Эльба + КУДиР + ВЭД

You are helping an ИП on ПСН who receives foreign currency income on overseas bank accounts (Jusan Kazakhstan, TBC Georgia, or similar). Convert their bank statement PDFs into three artifacts.

## Handling ambiguity — always ask, never guess

Wrong data corrupts the КУДиР and 181-И report — the user relies on these for taxes and валютный контроль. When the PDF is unclear, **stop and ask the user**. Do NOT fill in plausible-sounding defaults.

The two main ambiguity points:

1. **Counterparty is missing or opaque in the PDF** (some banks print only an IBAN or a cryptic code). Don't invent a name. Show the user the transaction (date, amount, direction, whatever identifier the PDF gave) and ask who it is. Once confirmed, save to `~/.config/ip-reports/contractors.json` so the next run of the same counterparty is automatic.
2. **VO code (181-И) classification is uncertain** — rules in `references/vo_codes.md` cover the typical cases but not every corner. When unclear, show the user the transaction and the 2–3 most plausible codes with their meanings, let them pick. Mark `"?"` only as a last resort when even the user can't decide.

Batch transactions when asking — if there are 5 unclear ones, present them as a numbered list in one message, not 5 separate prompts.

## Flow

### Step 1 — Profile check

Call the config module to verify the ИП profile exists:

```bash
cd <plugin_root>/skills/bank-statement-to-elba && python scripts/config.py wizard
```

If `~/.config/ip-reports/profile.json` is missing, run the wizard interactively. The wizard asks:

1. **ФИО** полностью (как в Эльбе)
2. **ИНН** (12 цифр для ИП)
3. **ОГРНИП** (15 цифр; опционально, можно пустым)
4. **Система налогообложения**: `PSN` / `USN_income` / `USN_income_minus_expense` / `OSNO`
5. **Используешь ли Контур.Эльбу для бухучёта?** (Y/n) — это ключевой вопрос. Если `N`, пропускаются вопросы про расчётный счёт/БИК и **не генерируется** `elba-import.txt` (только `journal.xlsx` + `summary.md`).
6. Если на шаге 5 был `Y` — **расчётный счёт РФ** (20 цифр, можно placeholder) и **БИК** (9 цифр, можно placeholder). Эльба сама создаст запись в "Реквизитах" при первом импорте.

**Онбординг нового контрагента** (когда в выписке появляется отправитель, которого нет в `~/.config/ip-reports/contractors.json`):

1. Спроси имя (например, "Blu Banyan Inc.").
2. **Если `profile.use_elba=True`** — объясни пользователю два пути, выбирает он:

   > В Эльбе поле «ИНН» в карточке контрагента **не обязательно** (её можно сохранить с пустым ИНН). Но Эльба **валидирует чексумму** — произвольные числа типа `9909999999` не пройдут.
   >
   > **Путь A — оставить ИНН пустым** (проще, но один раз руками):
   > 1. В Эльбе → «Контрагенты» → создай карточку, имя как в выписке (или короче), поле ИНН **пустое**, сохрани.
   > 2. Я сохраню `inn: ""` в `contractors.json`.
   > 3. При первом импорте файла Эльба попросит вручную привязать операцию к карточке. Дальше она **запомнит** связку по имени+счёту и будет матчить автоматически.
   >
   > **Путь B — валидный placeholder-ИНН** (автоматика с первого импорта):
   > 1. Сгенерируй placeholder с валидной чексуммой: `python scripts/config.py gen-inn 990900000` → выдаст что-то вроде `9909000004`. Префикс `9909` — официальный код ФНС для иностранных компаний, такое число Эльба примет. Используй разные 9-значные префиксы для разных контрагентов, чтобы не было коллизий.
   > 2. В Эльбе → «Контрагенты» → создай карточку, впиши этот ИНН → сохрани.
   > 3. Скажи мне этот же ИНН — я сохраню его в `contractors.json`. Матчинг по ИНН с первого импорта.
   >
   > Если у компании **реальный российский ИНН** (ООО в РФ) — просто дай его, это надёжнее всего.
   >
   > Какой путь выбираешь — A (пустой ИНН) или B (placeholder)?

3. **Если `profile.use_elba=False`** — ИНН не нужен для импорта; используй пустую строку (ренeрер подставит `0000000000` для форматной валидности, но файл всё равно не генерится).
4. Спроси тип операции и шаблон описания — или оставь дефолты (`"description_template": "поступление средств за {month} {year}"`).
5. Сохрани в `contractors.json` через `config.save_contractor(...)`.

**При обработке выписки, если у контрагента в `contractors.json` поле `inn` пустое и `profile.use_elba=True`** — это нормально (Путь A). Сгенерированный файл будет содержать `ПлательщикИНН=` (пусто) — Эльба при первом импорте попросит вручную выбрать контрагента, дальше запомнит. Просто **предупреди пользователя один раз**: «У контрагента X пустой ИНН — при первом импорте Эльба попросит вручную привязать операцию к карточке, дальше автоматом.» Не останавливай обработку.

### Step 2 — Read the PDF

Use the `Read` tool on the PDF path. Do NOT try regex parsers or pdfplumber — you are the parser. Extract:

- **Bank name** → one of `Jusan`, `Alatau`, `TBC`, or `Other`.
- **Account**: currency (3-letter), ISO numeric code (e.g. `840` for USD), account number/IBAN, opening balance, closing balance.
- **Period**: start and end dates (ISO `YYYY-MM-DD`).
- **All transactions** — incoming, outgoing, fees. Each must have:
  - `date` (ISO), `direction` (`in` / `out` / `fee`), `amount` (positive number), `currency`,
  - `counterparty` (at least `name`; **if the PDF does not name a counterparty, stop and ask the user** — see "Handling ambiguity" above — then save the resolved name to `contractors.json`),
  - `purpose` (original text), `reference` (FDF.../FEF.../etc.),
  - `vo_code` (see classification rules below),
  - `vo_description`.

### Step 3 — Classify each transaction by VO code

Read `references/vo_codes.md` and apply the rules:

- `direction=in` + foreign counterparty → **20200**.
- `direction=out` + counterparty is the user's own account (match by name / IBAN in profile / contractors) → **61100**.
- `direction=out`/`fee` + keywords «комиссия», `fee`, `maintenance`, `commission` → **80150**.
- **Uncertain? Ask the user.** Present the transaction (date, amount, direction, counterparty, purpose) and propose the 2–3 most plausible codes with short explanations. Accept their answer and use it. Only mark `"?"` if the user cannot decide either — then flag it in `summary.md` for later follow-up.

### Step 4 — Write extracted JSON

Produce a JSON matching `schemas/transactions.json`. Write to `out/<pdf_stem>/_extracted.json`.

### Step 5 — Run the renderer

```bash
cd <plugin_root>/skills/bank-statement-to-elba && python scripts/main.py --input out/<pdf_stem>/_extracted.json --out out/<pdf_stem>
```

This creates three files with names derived from bank + reporting period: `{Bank}-{period-slug}-elba-import.txt`, `{Bank}-{period-slug}-journal.xlsx`, `{Bank}-{period-slug}-summary.md`. Slug: `2025` for a full year, `2025-Q3` for a calendar quarter, `2025-07` for a full month, `2025-07-11_2025-09-26` for an arbitrary range. `_extracted.json` is deleted on success.

Example for Jusan, Q3 2025:
- `Jusan-2025-Q3-elba-import.txt`
- `Jusan-2025-Q3-journal.xlsx`
- `Jusan-2025-Q3-summary.md`

### Step 6 — Report to user

- How many transactions, how many incoming, total ₽ by CBR rate.
- Point to the generated `*-summary.md` for the Эльба post-import checklist.
- Flag any remaining `vo_code="?"` entries — should be rare since most ambiguity was resolved interactively during processing.
- List any new counterparties that were added to `contractors.json` this run.

## Batch mode

If multiple PDFs are given: process each independently (separate `out/<name>/`). After all are done, generate a combined `out/quarterly_summary.xlsx` that concatenates the «Журнал» sheets and merges the «ВЭД» data.

## Do NOT

- Invent a `vo_code`, counterparty, or purpose for ambiguous transactions — **ask the user first** (see "Handling ambiguity" above). Only mark `"?"` as a last resort after the user couldn't decide either.
- Silently skip a transaction with a missing counterparty or "normalize" it to a generic label — ask the user who it is and save the answer to `contractors.json` for future runs.
- Modify `elba_import.txt` by hand after `main.py` writes it.
- Commit `~/.config/ip-reports/` contents to any repository.
- Submit to `main.py` any transactions whose date has no CBR rate (CBR skips weekends/holidays; for such dates, use the prior business day's rate — the `cbr_rates.get_usd_rate` helper handles the fetch, not date adjustment; if you get a 404, walk back one day at a time).
