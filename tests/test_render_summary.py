import json
from pathlib import Path

from render_summary import render_summary_md


FIXTURE = Path(__file__).parent / "fixtures" / "sample_extracted.json"


def test_summary_includes_elba_postimport_steps(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = tmp_path / "summary.md"
    render_summary_md(
        extracted=data,
        total_rub=1000000.00,
        incoming_count=3,
        output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert "Начисление вознаграждения по агентскому договору" in text
    assert "Загрузить файл из банка" in text
    assert "bulk" in text.lower() or "массово" in text.lower()


def test_summary_mentions_ved_codes(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = tmp_path / "summary.md"
    render_summary_md(
        extracted=data,
        total_rub=1000000.00,
        incoming_count=3,
        output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert "20200" in text
    assert "61100" in text
    assert "80150" in text


def test_summary_has_totals(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = tmp_path / "summary.md"
    render_summary_md(
        extracted=data,
        total_rub=123456.78,
        incoming_count=3,
        output_path=out,
    )
    text = out.read_text(encoding="utf-8")
    assert "3" in text  # incoming count
    assert "123456.78" in text or "123 456.78" in text or "123456,78" in text
