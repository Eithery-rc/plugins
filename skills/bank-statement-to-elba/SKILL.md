---
name: bank-statement-to-elba
description: Use when user asks to process a foreign-bank PDF statement (Jusan KZ, TBC GE, or similar) into an Эльба-importable .txt file, a local КУДиР Excel journal, and a ВЭД 181-И report. Trigger phrases include "обработай выписку", "выписка в Эльбу", "1C из выписки", "КУДиР из PDF", "ВЭД по счёту", "statement to Elba".
---

# Bank statement → Эльба + КУДиР + ВЭД

You are helping an ИП on ПСН who receives foreign currency income on overseas bank accounts (Jusan Kazakhstan, TBC Georgia, or similar). Convert their bank statement PDFs into three artifacts.

## Flow

### Step 1 — Profile check

Call the config module to verify the ИП profile exists:

```bash
cd <plugin_root>/skills/bank-statement-to-elba && python scripts/config.py wizard
```

If `~/.config/ip-reports/profile.json` is missing, run the wizard interactively. Ask the user for: ФИО, ИНН, ОГРНИП (optional), система налогообложения, расчётный счёт (optional — placeholder OK), БИК (optional).

If `~/.config/ip-reports/contractors.json` does not have the sender of an incoming payment, prompt the user once and save.

### Step 2 — Read the PDF

Use the `Read` tool on the PDF path. Do NOT try regex parsers or pdfplumber — you are the parser. Extract:

- **Bank name** → one of `Jusan`, `Alatau`, `TBC`, or `Other`.
- **Account**: currency (3-letter), ISO numeric code (e.g. `840` for USD), account number/IBAN, opening balance, closing balance.
- **Period**: start and end dates (ISO `YYYY-MM-DD`).
- **All transactions** — incoming, outgoing, fees. Each must have:
  - `date` (ISO), `direction` (`in` / `out` / `fee`), `amount` (positive number), `currency`,
  - `counterparty` (at least `name`, if present also `account`, `country`),
  - `purpose` (original text), `reference` (FDF.../FEF.../etc.),
  - `vo_code` (see classification rules below),
  - `vo_description`.

### Step 3 — Classify each transaction by VO code

Read `references/vo_codes.md` and apply the rules:

- `direction=in` + foreign counterparty → **20200**.
- `direction=out` + counterparty is the user's own account (match by name / IBAN in profile / contractors) → **61100**.
- `direction=out`/`fee` + keywords «комиссия», `fee`, `maintenance`, `commission` → **80150**.
- Uncertain? Use `"?"` and note the user in summary.md. Do NOT guess.

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
- Flag any `vo_code="?"` entries that need manual classification.

## Batch mode

If multiple PDFs are given: process each independently (separate `out/<name>/`). After all are done, generate a combined `out/quarterly_summary.xlsx` that concatenates the «Журнал» sheets and merges the «ВЭД» data.

## Do NOT

- Invent `vo_code` for ambiguous transactions — mark `"?"` instead.
- Modify `elba_import.txt` by hand after `main.py` writes it.
- Commit `~/.config/ip-reports/` contents to any repository.
- Submit to `main.py` any transactions whose date has no CBR rate (CBR skips weekends/holidays; for such dates, use the prior business day's rate — the `cbr_rates.get_usd_rate` helper handles the fetch, not date adjustment; if you get a 404, walk back one day at a time).
