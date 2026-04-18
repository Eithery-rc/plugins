# ip-reports

Claude Code plugin for Russian ИП-ПСН reporting. Turns foreign-bank PDF statements (Jusan, TBC, ...) into:

- **`elba_import.txt`** — `1CClientBankExchange` file for «Деньги → Загрузить файл из банка» in Контур.Эльба.
- **`journal.xlsx`** — local КУДиР-style journal with three sheets (Журнал + ВЭД 181-И + Сводка).
- **`summary.md`** — human report + Эльба post-import checklist.

## Install

```
/plugin marketplace add Eithery-rc/plugins
/plugin install ip-reports@eithery
```

## First run

The skill triggers on phrases like «обработай выписку» or «1С из выписки». On first invocation:

1. Claude runs the profile wizard — 6 quick questions (ФИО, ИНН, ОГРНИП, система налогообложения, р/счёт, БИК). Answers save to `~/.config/ip-reports/profile.json`.
2. When it sees a new contractor for the first time, Claude asks for their details and saves to `~/.config/ip-reports/contractors.json`.

Neither file ever enters the plugin repo.

## Usage

Drop a PDF in front of Claude:

> обработай TBC_1_квартал.pdf

Artifacts land in `out/TBC_1_квартал/`. Open `summary.md` for the Эльба post-import checklist.

## What it does

1. Claude reads the PDF (AI-first — no brittle regex parsers; works across new bank statement layouts).
2. Extracts every movement (incoming, outgoing, fees) and classifies each by VO code (181-И).
3. Fetches CBR rates for transaction dates; converts USD → RUB.
4. Renders three files.

## What it does NOT do

- **Does not set «Тип операции» in Эльба** — the 1C format cannot control it. After import, bulk-edit the rows to «Начисление вознаграждения по агентскому договору».
- **Does not deduplicate** — Эльба neither does, so don't import the same file twice.
- **Does not cover every 181-И code** — MVP handles 20200 / 61100 / 80150; unknown codes are flagged in `summary.md`.
- **Does not generate the official КУДиР form 135н** — Эльба does that when you file.

## Development

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pytest
```

Design doc: originally in the sandbox `Nalogi/docs/superpowers/specs/2026-04-18-ip-reports-plugin-design.md`.

## License

MIT
