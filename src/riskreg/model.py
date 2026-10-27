"""Load a risk register from YAML and validate every field before any number is computed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

CONTROL_STATUSES = ["implemented", "partial", "planned"]
STRATEGIES = ["mitigate", "accept", "transfer", "avoid"]
CSF_FUNCTIONS = {"GV": "Govern", "ID": "Identify", "PR": "Protect", "DE": "Detect", "RS": "Respond", "RC": "Recover"}
CSF_PATTERN = re.compile(r"^(GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-\d{2}$")
# ISO/IEC 27001:2022 Annex A has 93 controls: 5.1-5.37, 6.1-6.8, 7.1-7.14, 8.1-8.34.
ISO_RANGES = {5: 37, 6: 8, 7: 14, 8: 34}
ISO_THEMES = {5: "Organizational", 6: "People", 7: "Physical", 8: "Technological"}
ISO_PATTERN = re.compile(r"^A\.(\d)\.(\d{1,2})$")
# Qualitative rating bands for likelihood x impact (1-25).
BANDS = [(20, "critical"), (12, "high"), (6, "medium"), (1, "low")]


class RegisterError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


def rating(score: int) -> str:
    return next(name for floor, name in BANDS if score >= floor)


@dataclass
class Score:
    likelihood: int
    impact: int

    @property
    def value(self) -> int:
        return self.likelihood * self.impact

    @property
    def rating(self) -> str:
        return rating(self.value)


@dataclass
class Range3:
    """Minimum, most likely and maximum estimate, as a FAIR analyst would elicit it."""

    low: float
    mode: float
    high: float


@dataclass
class Estimate:
    frequency: Range3  # loss events per year
    magnitude: Range3  # loss per event, in the register's currency


@dataclass
class Control:
    name: str
    status: str
    nist_csf: list[str] = field(default_factory=list)
    iso27001: list[str] = field(default_factory=list)


@dataclass
class Treatment:
    strategy: str
    plan: str = ""
    owner: str = ""
    due: date | None = None
    cost: float = 0.0  # annualized cost of the treatment
    after: Estimate | None = None


@dataclass
class Risk:
    id: str
    title: str
    category: str
    owner: str
    inherent: Score
    residual: Score
    estimate: Estimate
    description: str = ""
    controls: list[Control] = field(default_factory=list)
    treatment: Treatment | None = None
    review_date: date | None = None


@dataclass
class Appetite:
    max_residual_score: int = 9
    max_annual_loss_p90: float | None = None


@dataclass
class Register:
    organization: str
    assessment_date: date
    currency: str
    appetite: Appetite
    risks: list[Risk]


def _int_1_5(value, where: str, problems: list[str]) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
        problems.append(f"{where} must be a whole number from 1 to 5")
        return 1
    return value


def _score(raw, where: str, problems: list[str]) -> Score:
    if not isinstance(raw, dict):
        problems.append(f"{where} needs likelihood and impact")
        return Score(1, 1)
    return Score(
        _int_1_5(raw.get("likelihood"), f"{where}.likelihood", problems),
        _int_1_5(raw.get("impact"), f"{where}.impact", problems),
    )


def _range(raw, where: str, problems: list[str]) -> Range3:
    if not (isinstance(raw, list) and len(raw) == 3 and all(isinstance(v, int | float) for v in raw)):
        problems.append(f"{where} must be [min, most likely, max]")
        return Range3(0, 0, 0)
    low, mode, high = (float(v) for v in raw)
    if low < 0 or not low <= mode <= high:
        problems.append(f"{where} must satisfy 0 <= min <= most likely <= max")
    return Range3(low, mode, high)


def _estimate(raw, where: str, problems: list[str]) -> Estimate:
    raw = raw if isinstance(raw, dict) else {}
    return Estimate(
        _range(raw.get("frequency"), f"{where}.frequency", problems),
        _range(raw.get("magnitude"), f"{where}.magnitude", problems),
    )


def _check_csf(ref: str, where: str, problems: list[str]) -> None:
    if not CSF_PATTERN.match(ref):
        problems.append(f"{where}: '{ref}' is not a NIST CSF 2.0 subcategory ID like PR.AA-03")


def _check_iso(ref: str, where: str, problems: list[str]) -> None:
    m = ISO_PATTERN.match(ref)
    if not m or int(m.group(1)) not in ISO_RANGES or not 1 <= int(m.group(2)) <= ISO_RANGES[int(m.group(1))]:
        problems.append(f"{where}: '{ref}' is not an ISO/IEC 27001:2022 Annex A control (A.5.1 to A.8.34)")


def _date(value, where: str, problems: list[str]) -> date | None:
    if value is None or isinstance(value, date):
        return value
    problems.append(f"{where} must be a date like 2026-12-31")
    return None


def _risk(raw: dict, problems: list[str]) -> Risk | None:
    rid = str(raw.get("id", "?"))
    missing = [k for k in ("id", "title", "category", "owner", "inherent", "residual", "fair") if not raw.get(k)]
    if missing:
        problems.append(f"{rid}: missing {', '.join(missing)}")
        return None
    inherent = _score(raw["inherent"], f"{rid}.inherent", problems)
    residual = _score(raw["residual"], f"{rid}.residual", problems)
    if residual.value > inherent.value:
        problems.append(f"{rid}: residual score is higher than inherent; controls cannot increase risk")

    controls = []
    for i, c in enumerate(raw.get("controls") or [], 1):
        where = f"{rid}.controls[{i}]"
        status = c.get("status", "")
        if status not in CONTROL_STATUSES:
            problems.append(f"{where}.status must be one of {', '.join(CONTROL_STATUSES)}")
        csf = [str(x) for x in c.get("nist_csf") or []]
        iso = [str(x) for x in c.get("iso27001") or []]
        for ref in csf:
            _check_csf(ref, where, problems)
        for ref in iso:
            _check_iso(ref, where, problems)
        controls.append(Control(str(c.get("name", "")), status, csf, iso))

    treatment = None
    if raw.get("treatment"):
        t = raw["treatment"]
        strategy = t.get("strategy", "")
        if strategy not in STRATEGIES:
            problems.append(f"{rid}.treatment.strategy must be one of {', '.join(STRATEGIES)}")
        cost = t.get("cost", 0)
        if not isinstance(cost, int | float) or cost < 0:
            problems.append(f"{rid}.treatment.cost must be a number >= 0")
            cost = 0
        treatment = Treatment(
            strategy=strategy,
            plan=str(t.get("plan", "")).strip(),
            owner=str(t.get("owner", "")),
            due=_date(t.get("due"), f"{rid}.treatment.due", problems),
            cost=float(cost),
            after=_estimate(t["after"], f"{rid}.treatment.after", problems) if t.get("after") else None,
        )

    return Risk(
        id=rid,
        title=str(raw["title"]),
        category=str(raw["category"]),
        owner=str(raw["owner"]),
        inherent=inherent,
        residual=residual,
        estimate=_estimate(raw["fair"], f"{rid}.fair", problems),
        description=str(raw.get("description", "")).strip(),
        controls=controls,
        treatment=treatment,
        review_date=_date(raw.get("review_date"), f"{rid}.review_date", problems),
    )


def load(path: str | Path) -> Register:
    problems: list[str] = []
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RegisterError([f"not valid YAML: {exc}"]) from exc
    for key in ("organization", "assessment_date", "risks"):
        if not data.get(key):
            problems.append(f"missing top-level '{key}'")
    if problems:
        raise RegisterError(problems)

    appetite_raw = data.get("appetite") or {}
    appetite = Appetite(
        max_residual_score=int(appetite_raw.get("max_residual_score", 9)),
        max_annual_loss_p90=appetite_raw.get("max_annual_loss_p90"),
    )
    risks = [r for r in (_risk(raw, problems) for raw in data["risks"]) if r]
    ids = [r.id for r in risks]
    problems += [f"duplicate risk id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    assessed = _date(data["assessment_date"], "assessment_date", problems)
    if problems:
        raise RegisterError(problems)
    return Register(
        organization=str(data["organization"]),
        assessment_date=assessed,
        currency=str(data.get("currency", "USD")),
        appetite=appetite,
        risks=risks,
    )
