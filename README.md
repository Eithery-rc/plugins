# ip-reports

Claude Code plugin for Russian ИП-ПСН reporting. Turns foreign-bank PDF statements (Jusan, TBC, ...) into:

- **`{Bank}-{period}-elba-import.txt`** — `1CClientBankExchange` file for «Деньги → Загрузить файл из банка» in Контур.Эльба.
- **`{Bank}-{period}-journal.xlsx`** — local КУДиР-style journal with three sheets (Журнал + ВЭД 181-И + Сводка).
- **`{Bank}-{period}-summary.md`** — human report + Эльба post-import checklist.

Example filenames for a Q3 2025 Jusan statement: `Jusan-2025-Q3-elba-import.txt`, `Jusan-2025-Q3-journal.xlsx`, `Jusan-2025-Q3-summary.md`. Period slug auto-detects calendar quarter / full year / full month; otherwise falls back to `YYYY-MM-DD_YYYY-MM-DD`.

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

Artifacts land in `out/TBC_1_квартал/`. Open the `*-summary.md` for the Эльба post-import checklist.

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

## Recommended companion skills

Anthropic maintains an official skills marketplace with high-quality document-handling skills (Word, Excel, PowerPoint, PDF). Install it alongside this one:

```
/plugin marketplace add anthropics/skills
```

Then install whichever you need:

```
/plugin install docx@anthropic-skills    # .docx reading/writing
/plugin install xlsx@anthropic-skills    # .xlsx reading/writing
/plugin install pptx@anthropic-skills    # .pptx reading/writing
/plugin install pdf@anthropic-skills     # PDF handling
```

(Marketplace name may differ — check with `/plugin marketplace list` after adding.)

These four are **source-available, not open source** (© 2025 Anthropic, PBC; redistribution forbidden). Install directly from Anthropic's repo — we don't mirror them. Other skills in their marketplace (`mcp-builder`, `skill-creator`, `frontend-design`, etc.) are Apache 2.0.

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
