"""efe_city.report - ODF (OPTIBEST Document Format) generator: text templates + computed tables.
Placeholders: {{dotted.path|format}} inline, and {{table:NAME}} alone on a line. Missing keys raise (fail loudly)."""
from __future__ import annotations

import re
import textwrap

from .core import PKG, EfeError, run_all
from . import evaluate as ev

W = 79
DBL, SGL = "═" * W, "─" * W
TABLES = {}


def table_fn(name):
    def deco(fn):
        TABLES[name] = fn
        return fn
    return deco


def para(text, indent=0):
    return textwrap.wrap(text, W - indent, initial_indent=" " * indent, subsequent_indent=" " * indent)


def block(label, lines, spec=False):
    tl, bl, v, h = ("╔═", "╚", "║", "═") if spec else ("┌─", "└", "│", "─")
    head = f"{tl} {label} ".ljust(W, h)
    out = [head, v]
    for ln in lines:
        for w in (textwrap.wrap(ln, W - 3) or [""]):
            out.append(f"{v}  {w}")
    out += [v, bl.ljust(W, h)]
    return out


def table(headers, rows, widths=None, aligns=None, indent=0):
    rows = [[str(c) for c in r] for r in rows]
    headers = [str(h) for h in headers]
    n = len(headers)
    nat = [max([len(headers[i])] + [len(r[i]) for r in rows]) for i in range(n)]
    avail = W - indent - 3 * (n - 1)
    widths = list(widths) if widths else nat[:]
    guard = 0
    while sum(widths) > avail and guard < 500:
        i = max(range(n), key=lambda j: widths[j])
        widths[i] -= 1
        guard += 1
        if widths[i] < 5:
            raise EfeError(f"table too wide for {W} columns: {headers}")
    out = []

    def fmt(cells):
        wr = [textwrap.wrap(c, widths[i]) or [""] for i, c in enumerate(cells)]
        for ln in range(max(len(x) for x in wr)):
            parts = []
            for i in range(n):
                t = wr[i][ln] if ln < len(wr[i]) else ""
                parts.append(t.rjust(widths[i]) if aligns and aligns[i] == "r" else t.ljust(widths[i]))
            out.append((" " * indent + " │ ".join(parts)).rstrip())
    fmt(headers)
    out.append(" " * indent + "─┼─".join("─" * w for w in widths))
    for r in rows:
        fmt(r)
    return out


def kv(pairs, key_w=34):
    out = []
    for k, v in pairs:
        lines = textwrap.wrap(str(v), W - key_w - 3) or [""]
        out.append(f"{k.ljust(key_w)} : {lines[0]}")
        out += [" " * (key_w + 3) + x for x in lines[1:]]
    return out


PH = re.compile(r"\{\{\s*([^{}|:]+?)\s*(?:\|\s*([^{}]*?)\s*)?\}\}")
TB = re.compile(r"^\{\{\s*table:(\w+)\s*\}\}\s*$")


def lookup(ctx, path):
    cur = ctx
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, (list, tuple)) and part.lstrip("-").isdigit():
            cur = cur[int(part)]
        else:
            raise EfeError(f"template key '{path}' missing at '{part}'")
    return cur


def render(text, ctx):
    """Directives: @DBL @SGL @H1 t @H2 t @P text @L text @BLOCK label..@END @SPEC label..@END ; {{table:x}} ; {{path|fmt}}"""
    out, buf, label, spec = [], None, "", False

    def sub(mm):
        v = lookup(ctx, mm.group(1))
        if mm.group(2):
            return format(v, mm.group(2))
        if isinstance(v, bool):
            return "yes" if v else "no"
        return f"{v:.4g}" if isinstance(v, float) else str(v)
    for raw in text.splitlines():
        m = TB.match(raw)
        if m:
            if m.group(1) not in TABLES:
                raise EfeError(f"unknown table '{m.group(1)}'")
            out += TABLES[m.group(1)](ctx)
            continue
        line = PH.sub(sub, raw)
        if buf is not None:
            if line.strip() == "@END":
                out += block(label, buf, spec)
                buf = None
            else:
                buf.append(line)
            continue
        if line.startswith(("@BLOCK ", "@SPEC ")):
            if out and out[-1] != "":
                out.append("")
            spec, label, buf = line.startswith("@SPEC"), line.split(" ", 1)[1], []
        elif line == "@DBL":
            out.append(DBL)
        elif line == "@SGL":
            out.append(SGL)
        elif line.startswith("@H1 "):
            out += ["", "", SGL, line[4:].upper(), SGL, ""]
        elif line.startswith("@H2 "):
            out += ["", line[4:], ""]
        elif line.startswith("@P "):
            if out and out[-1] != "":
                out.append("")
            out += textwrap.wrap(line[3:], W) + [""]
        elif line.startswith("@L "):
            if out and out[-1] != "" and not out[-1].startswith(("• ", "  ")):
                out.append("")
            out += textwrap.wrap(line[3:], W, initial_indent="• ", subsequent_indent="  ")
        else:
            if len(line) > W:
                ctx.setdefault("_problems", []).append(f"{len(line)} cols: {line[:70]}")
            out.append(line)
    if buf is not None:
        raise EfeError("unterminated @BLOCK")
    return "\n".join(out) + "\n"


def build(cfg, an, template_dir=None):
    from . import tables  # noqa: F401  (registers TABLES)
    res = run_all(cfg)
    x = ev.evaluate(cfg)
    L, g = res["land"], cfg["geometry"]
    a = g["cell_apothem_m"]
    R = 2 * a / 1.7320508075688772
    ctx = {"cfg": cfg, "res": res, "k": x["k"], "s": x["s"], "dims": x["dims"], "an": an, "gates": x["gates"],
           "d": {"pop_ward": L["pop_cell"] * g["cells_per_ward"], "ward_ha": L["hex"]["area_ha"] * g["cells_per_ward"],
                 "ward_diam_m": 2 * (2 * a + R), "flat2flat": 2 * a, "city_km2": L["city"]["total_m2"] / 1e6,
                 "ponds_ha_city": cfg["water"]["pond_m3_pp"] / cfg["water"]["pond_depth_m"] * L["city"]["pop"] / 1e4,
                 "gates_ok": sum(q["ok"] for q in x["gates"]), "top_ext": res["economics"]["priority"][0][0].replace("_", " "), "gates_n": len(x["gates"]),
                 "date": "2026-10-16", "ladder_n": len(an["ladder"]), "n_open": 10,
                 "pv_kwp_dwelling": res["energy"]["hen"]["pv_kwp"], "wet_depth": 1.8,
                 "pond_evap_cut": 100 * 0.8 * (cfg["water"]["pond_pv_cover"] if cfg["energy"]["pond_pv"] else 0.0),
                 "pv_jun_dec": res["energy"]["monthly"][5]["gen"] / res["energy"]["monthly"][11]["gen"],
                 "facade_ratio": res["energy"]["facade_yield"] / res["energy"]["opt_yield"]}}
    tdir = template_dir or PKG / "templates"
    parts = []
    for p in sorted(tdir.glob("*.odf")):
        n0 = len(ctx.get("_problems", []))
        parts.append(render(p.read_text(encoding="utf-8"), ctx))
        for q in ctx.get("_problems", [])[n0:]:
            print(f"[{p.name}] {q}")
    if ctx.get("_problems"):
        raise EfeError(f"{len(ctx['_problems'])} template lines exceed {W} columns (see above)")
    return "".join(parts)
