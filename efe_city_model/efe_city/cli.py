"""efe_city.cli - scriptable entry points:  python -m efe_city <run|check|analyze|draw|build> [--config F] [--set k=v ...] [--out DIR]"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .core import EfeError, load_config, run_all


def _cfg(a):
    return load_config(a.config, a.set)


def cmd_run(a):
    from . import evaluate as ev
    x = ev.evaluate(_cfg(a))
    print(f"composite {x['composite']:.4f} | dims " + " ".join(f"{k[:4]}={v:.2f}" for k, v in x["dims"].items()))
    for n, v in x["k"].items():
        print(f"  {n:20s} {v:12.4f}")
    for g in x["gates"]:
        print(f"  [{'PASS' if g['ok'] else 'FAIL'}] {g['id']} {g['text']} ({g['value']:.3g})")
    if a.json:
        pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(a.out) / "run.json").write_text(json.dumps({"k": x["k"], "composite": x["composite"], "gates": x["gates"]}, indent=1, default=str))
    return 0


def cmd_check(a):
    from . import evaluate as ev
    x = ev.evaluate(_cfg(a))
    bad = [g for g in x["gates"] if not g["ok"]]
    for g in bad:
        print(f"FAIL {g['id']} {g['text']} ({g['value']:.3g})")
    print(f"{len(x['gates']) - len(bad)}/{len(x['gates'])} gates pass | composite {x['composite']:.4f}")
    return 1 if bad else 0


def cmd_analyze(a):
    from . import analysis
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = analysis.run_analysis(_cfg(a), quick=a.quick)
    (out / "analysis.json").write_text(json.dumps(data, indent=1, default=str))
    print(f"analysis written to {out / 'analysis.json'} in {data['seconds']:.0f}s | plateau={data['plateau']['plateau']}")
    return 0


def cmd_draw(a):
    from . import drawings
    cfg = _cfg(a)
    names = drawings.draw_all(cfg, run_all(cfg), a.out)
    print("wrote", ", ".join(names))
    return 0


def cmd_build(a):
    from . import analysis, report
    cfg = _cfg(a)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ap = out / "analysis.json"
    data = json.loads(ap.read_text()) if ap.exists() else analysis.run_analysis(cfg, quick=a.quick)
    ap.write_text(json.dumps(data, indent=1, default=str))
    txt = report.build(cfg, data)
    (out / "AEQUCITY_v2.0_BLUEPRINT.odf.txt").write_text(txt, encoding="utf-8")
    (out / "AEQUCITY_v2.0_BLUEPRINT.md").write_text("```text\n" + txt + "```\n", encoding="utf-8")
    print(f"blueprint: {len(txt.splitlines())} lines")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="efe_city", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", cmd_run), ("check", cmd_check), ("analyze", cmd_analyze), ("draw", cmd_draw), ("build", cmd_build)):
        sp = sub.add_parser(name)
        sp.add_argument("--config")
        sp.add_argument("--set", action="append", default=[], metavar="KEY=JSON")
        sp.add_argument("--out", default="out")
        sp.add_argument("--json", action="store_true")
        sp.add_argument("--quick", action="store_true")
        sp.set_defaults(fn=fn)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except EfeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
