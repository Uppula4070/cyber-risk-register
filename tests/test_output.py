import json

from riskreg.charts import money, nice_max
from riskreg.cli import main
from riskreg.model import load
from riskreg.report import build
from riskreg.simulate import run
from riskreg.summary import decisions


def test_money():
    assert [money(v) for v in (950, 12_500, 1_000_000, 2_940_000)] == ["$950", "$12K", "$1M", "$2.94M"]
    assert money(5000, "EUR") == "5K EUR"


def test_nice_max():
    assert [nice_max(v) for v in (0.9, 870_000, 1_900_000, 4_100_000)] == [1, 1_000_000, 2_000_000, 5_000_000]


def test_decisions(sample):
    reg = load(sample)
    text = " ".join(decisions(reg, run(reg, years=3000)))
    assert "Approve the mitigate plan for R-01" in text
    assert "Re-examine the treatment for R-10" in text
    assert "R-06 was due for review on 2026-10-01" in text


def test_untreated_risk_above_appetite_needs_owner_decision(edit_register):
    path = edit_register(lambda d: d["risks"][4].update(residual={"likelihood": 3, "impact": 4}))  # R-05, no treatment
    reg = load(path)
    assert any("R-05 is above appetite" in d and "formally accept" in d for d in decisions(reg, run(reg, years=2000)))


def test_report_escapes_register_text(edit_register):
    reg = load(edit_register(lambda d: d["risks"][0].update(title="<script>alert(1)</script>")))
    html = build(reg, run(reg, years=500))
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html


def test_report_sections(sample):
    reg = load(sample)
    html = build(reg, run(reg, years=500))
    for text in ["Decisions needed", "Loss exceedance curve", "Treatment plan", "NIST CSF 2.0", "ISO/IEC 27001:2022"]:
        assert text in html
    assert html.count('class="heatmap"') == 2


def test_cli(sample, tmp_path, capsys):
    html, md, js = tmp_path / "r.html", tmp_path / "s.md", tmp_path / "r.json"
    args = [str(sample), "-o", str(html), "--summary", str(md), "--json", str(js), "--years", "1000"]
    assert main(args) == 0
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert md.read_text(encoding="utf-8").startswith("# Cyber risk summary")
    assert len(json.loads(js.read_text(encoding="utf-8"))) == 10
    assert "expected annual loss" in capsys.readouterr().out


def test_cli_validate_and_errors(sample, edit_register, capsys):
    assert main([str(sample), "--validate"]) == 0
    bad = edit_register(lambda d: d["risks"][0]["inherent"].update(impact=9))
    assert main([str(bad), "--validate"]) == 2
    assert "from 1 to 5" in capsys.readouterr().err
