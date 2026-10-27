import pytest

from riskreg.model import RegisterError, Score, load, rating


def test_loads_sample(sample):
    reg = load(sample)
    assert len(reg.risks) == 10
    assert reg.appetite.max_residual_score == 9
    assert reg.risks[0].controls[0].nist_csf == ["PR.DS-11", "RC.RP-03"]


@pytest.mark.parametrize(
    ("score", "band"),
    [(1, "low"), (5, "low"), (6, "medium"), (11, "medium"), (12, "high"), (20, "critical"), (25, "critical")],
)
def test_rating_bands(score, band):
    assert rating(score) == band


def test_score_value():
    assert Score(4, 5).value == 20 and Score(4, 5).rating == "critical"


def _expect(path, message):
    with pytest.raises(RegisterError) as exc:
        load(path)
    assert any(message in p for p in exc.value.problems), exc.value.problems


def test_rejects_score_out_of_range(edit_register):
    _expect(edit_register(lambda d: d["risks"][0]["inherent"].update(likelihood=6)), "from 1 to 5")


def test_rejects_residual_above_inherent(edit_register):
    _expect(edit_register(lambda d: d["risks"][8]["residual"].update(impact=5)), "controls cannot increase risk")


def test_rejects_bad_csf_id(edit_register):
    _expect(
        edit_register(lambda d: d["risks"][0]["controls"][0].update(nist_csf=["PR.AC-1"])),
        "not a NIST CSF 2.0 subcategory",
    )


@pytest.mark.parametrize("ref", ["A.5.38", "A.6.9", "A.9.1", "A.8.0", "8.24"])
def test_rejects_bad_iso_id(edit_register, ref):
    _expect(edit_register(lambda d: d["risks"][0]["controls"][0].update(iso27001=[ref])), "ISO/IEC 27001:2022")


def test_accepts_iso_boundaries(edit_register):
    path = edit_register(
        lambda d: d["risks"][0]["controls"][0].update(iso27001=["A.5.37", "A.6.8", "A.7.14", "A.8.34"])
    )
    assert load(path).risks[0].controls[0].iso27001[-1] == "A.8.34"


def test_rejects_unordered_estimate(edit_register):
    _expect(
        edit_register(lambda d: d["risks"][0]["fair"].update(frequency=[0.5, 0.1, 0.3])), "min <= most likely <= max"
    )


def test_rejects_unknown_strategy_and_status(edit_register):
    def change(d):
        d["risks"][0]["treatment"]["strategy"] = "ignore"
        d["risks"][1]["controls"][0]["status"] = "done"

    with pytest.raises(RegisterError) as exc:
        load(edit_register(change))
    assert len(exc.value.problems) == 2  # every problem reported at once


def test_rejects_duplicate_ids(edit_register):
    _expect(edit_register(lambda d: d["risks"][1].update(id="R-01")), "duplicate risk id R-01")


def test_rejects_missing_fields(edit_register):
    _expect(edit_register(lambda d: d["risks"][2].pop("fair")), "R-03: missing fair")
