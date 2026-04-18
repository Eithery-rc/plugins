# ip-reports

Claude Code plugin for Russian ИП reporting. Turns foreign-bank PDF statements (Jusan KZ, TBC GE, ...) into:

- `elba_import.txt` — 1CClientBankExchange file for import into Контур.Эльба
- `journal.xlsx` — local income journal + 181-И ВЭД report
- `summary.md` — what was done + post-import steps

Design: see `docs/design.md` (copied from sandbox during development).

## Install (Claude Code)

```
/plugin install <user>/ip-reports
```

On first run the skill will walk you through a 6-question wizard and write your details to `~/.config/ip-reports/profile.json`.

## Usage

Drop a bank statement PDF in front of Claude and say:

> обработай TBC_1_квартал.pdf

Claude will read the PDF, extract all movements, classify by VO code, and write artifacts into `out/<pdf_name>/`.

## Development

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
pytest
```
