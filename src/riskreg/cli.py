from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .charts import money
from .model import RegisterError, load
from .report import build
from .simulate import DEFAULT_SEED, DEFAULT_YEARS, run
from .summary import findings, markdown


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="riskreg",
        description="Cyber risk register: validate, score, map to NIST CSF / ISO 27001 and simulate annual loss.",
    )
    p.add_argument("register", help="risk register YAML file")
    p.add_argument("-o", "--output", default="report.html", help="HTML report to write")
    p.add_argument("--summary", metavar="FILE", help="also write a Markdown board summary")
    p.add_argument("--json", metavar="FILE", help="also write per-risk results as JSON")
    p.add_argument("--years", type=int, default=DEFAULT_YEARS, help=f"simulated years (default {DEFAULT_YEARS:,})")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed, for repeatable results")
    p.add_argument("--validate", action="store_true", help="only check the register for mistakes")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        reg = load(args.register)
    except RegisterError as exc:
        print("The register has problems to fix:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2
    if args.validate:
        print(f"OK: {len(reg.risks)} risks")
        return 0

    p = run(reg, years=args.years, seed=args.seed)
    Path(args.output).write_text(build(reg, p), encoding="utf-8")
    if args.summary:
        Path(args.summary).write_text(markdown(reg, p), encoding="utf-8")
    if args.json:
        rows = [
            {
                "id": r.risk.id,
                "title": r.risk.title,
                "residual_score": r.risk.residual.value,
                "residual_rating": r.risk.residual.rating,
                "expected_annual_loss": round(r.current.mean),
                "p50": round(r.current.p50),
                "p90": round(r.current.p90),
                "above_appetite": r.above_appetite,
                "rosi": None if r.rosi is None else round(r.rosi, 2),
            }
            for r in p.results
        ]
        Path(args.json).write_text(json.dumps(rows, indent=2), encoding="utf-8")

    for line in findings(reg, p):
        print(line)
    print(f"wrote {args.output} (portfolio 1-in-10 year loss {money(p.current.p90, reg.currency)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
