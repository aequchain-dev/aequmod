"""efe_city.drawings - parametric SVG schematics generated from the same config/results as the blueprint."""
from __future__ import annotations

import html
import math

from .core import SQ3

COL = {"green": "#7fae6b", "permeable_walk": "#d9cdb4", "permeable_street": "#bfa98a", "ribbon": "#8c8c8c"}


def _svg(w, h, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="DejaVu Sans, Arial, sans-serif">\n<defs>{defs}</defs>\n'
            f'<rect width="{w}" height="{h}" fill="#faf8f2"/>\n' + "\n".join(body) + "\n</svg>\n")


def _t(x, y, s, size=13, anchor="start", fill="#222", weight="normal", rot=None):
    tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}"{tr}>{html.escape(str(s), quote=False)}</text>')


def ward_plan_svg(cfg, res):
    g, L = cfg["geometry"], res["land"]
    a = float(g["cell_apothem_m"])
    R = 2 * a / SQ3
    s, W, H, cx, cy = 0.50, 1500, 1260, 720, 650
    P = lambda X, Y: (cx + s * X, cy - s * Y)
    ang = [30 + 60 * k for k in range(6)]
    centres = [(0.0, 0.0)] + [(2 * a * math.cos(math.radians(t)), 2 * a * math.sin(math.radians(t))) for t in ang]
    defs = ('<pattern id="agri" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
            '<rect width="14" height="14" fill="#dbe9c6"/><line x1="0" y1="0" x2="0" y2="14" stroke="#b7d28f" stroke-width="5"/></pattern>'
            '<pattern id="pv" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#6bb7d9"/>'
            '<line x1="0" y1="8" x2="8" y2="0" stroke="#f2b632" stroke-width="2"/></pattern>')
    body = []
    rw = (2 * a + R + 190) * s
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{rw:.1f}" fill="url(#agri)" stroke="#8fb36a" stroke-width="2" stroke-dasharray="10 6"/>')
    body.append(_t(cx, cy - rw - 12, "AGRI-COMMONS WEDGE + NATURE CORRIDORS (ward belt)", 15, "middle", "#4c7a2e", "bold"))
    verts = lambda c: [(c[0] + R * math.cos(math.radians(60 * i)), c[1] + R * math.sin(math.radians(60 * i))) for i in range(6)]
    for c in centres:
        pts = " ".join("%.1f,%.1f" % P(*v) for v in verts(c))
        body.append(f'<polygon points="{pts}" fill="#efe8d6" stroke="none"/>')
    edges = {}
    for c in centres:
        v = verts(c)
        for i in range(6):
            p, q = v[i], v[(i + 1) % 6]
            key = tuple(sorted(((round(p[0]), round(p[1])), (round(q[0]), round(q[1])))))
            edges[key] = (p, q)
    for w_m, col, dash in ((g["seam_width_m"], "#b9a98a", None), (8.0, "#5d9a4c", None), (3.0, "#3b8fc0", None), (2.2, "#f2b632", "6 5")):
        for p, q in edges.values():
            x1, y1 = P(*p); x2, y2 = P(*q)
            d = f' stroke-dasharray="{dash}"' if dash else ""
            body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w_m * s:.1f}" stroke-linecap="round"{d}/>')
    nst = max(1, round(L["n_courts"] / 6))
    pr = math.sqrt(g["node_area_ha"] * 1e4 / math.pi)
    for c in centres:
        for t in ang:
            ux, uy = math.cos(math.radians(t)), math.sin(math.radians(t))
            x1, y1 = P(c[0], c[1]); x2, y2 = P(c[0] + a * ux, c[1] + a * uy)
            body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#cdb892" stroke-width="{g["lane_width_m"] * s:.1f}"/>')
            r0, ln = pr + 25, a - pr - 55
            for j in range(nst):
                r = r0 + (j + 0.5) * ln / nst
                side = 1 if j % 2 == 0 else -1
                bx, by = c[0] + r * ux, c[1] + r * uy
                ex, ey = bx - side * g["court_lane_m"] * uy, by + side * g["court_lane_m"] * ux
                xa, ya = P(bx, by); xb, yb = P(ex, ey)
                body.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="#cdb892" stroke-width="{g["lane_width_m"] * s:.1f}" stroke-linecap="round"/>')
        px, py = P(*c)
        body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pr * s:.1f}" fill="#e9b872" stroke="#b9772a" stroke-width="1.5"/>')
    px, py = P(0, 0)
    body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pr * s * 1.7:.1f}" fill="none" stroke="#b9772a" stroke-width="3" stroke-dasharray="4 3"/>')
    body.append(_t(px, py + 4, "WARD NODE", 13, "middle", "#5b3a0a", "bold"))
    pond_r = math.sqrt(cfg["water"]["pond_m3_pp"] / cfg["water"]["pond_depth_m"] * L["city"]["pop"] / (g["wards"] * 6) / math.pi)
    for k in range(6):
        t = 60 * k
        X, Y = (2 * a + R + 95) * math.cos(math.radians(t)), (2 * a + R + 95) * math.sin(math.radians(t))
        x, y = P(X, Y)
        body.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{pond_r * s * 1.3:.1f}" ry="{pond_r * s:.1f}" fill="url(#pv)" stroke="#2d7aa3" stroke-width="2"/>')
    x0, y0 = P(-R - 70, -a)
    x1, y1 = P(-R - 70, a)
    body.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#222" stroke-width="1.5" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    body.append(_t(x0 - 8, (y0 + y1) / 2, f"{2 * a:.0f} m (flat-to-flat)", 13, "middle", "#222", "normal", -90))
    sun = "N" if res["climate"]["lat"] < 0 else "S"
    body.append(_t(1400, 60, "N", 22, "middle", "#222", "bold"))
    body.append('<polygon points="1400,70 1388,110 1400,102 1412,110" fill="#222"/>')
    body.append(_t(1400, 132, f"sun side = {sun}", 12, "middle"))
    sb = 200 * s
    body.append(f'<line x1="1180" y1="1200" x2="{1180 + sb:.1f}" y2="1200" stroke="#222" stroke-width="3"/>' + _t(1180 + sb / 2, 1190, "200 m", 13, "middle"))
    t = [("AEQUCITY v2.0 | WARD PLAN (7 cells) | SCHEMATIC S-01", 20, "bold"),
         (f"cell: apothem {a:.0f} m | area {L['hex']['area_ha']:.1f} ha | pop {L['pop_cell']:.0f} | density {g['gross_density_p_ha']} p/ha", 13, "normal"),
         (f"ward: {g['cells_per_ward']} cells | pop {L['pop_cell'] * g['cells_per_ward']:.0f} | city: {g['wards']} wards, {L['city']['pop']:.0f} p, R {L['city']['radius_km']:.1f} km", 13, "normal"),
         (f"seam {g['seam_width_m']} m (AEQUSPINE) | lane {g['lane_width_m']} m | path {g['path_width_m']} m | node {g['node_area_ha']} ha | courts/cell {L['n_courts']:.0f}", 13, "normal")]
    for i, (txt, sz, wt) in enumerate(t):
        body.append(_t(30, 40 + i * 22, txt, sz, "start", "#222", wt))
    leg = [("#b9a98a", "seam street (slow, shared)"), ("#5d9a4c", "median: swale + cycle track + PV colonnade"), ("#3b8fc0", "bio-swale / flood route"),
           ("#cdb892", "lane (shared surface) + court stubs"), ("#e9b872", "cell node: market, school, hygiene hub, shelter"),
           ("url(#pv)", "pond + floating PV (water reserve)"), ("url(#agri)", "agri-commons wedge / habitat")]
    for i, (c, txt) in enumerate(leg):
        yy = 1010 + i * 26
        body.append(f'<rect x="30" y="{yy}" width="26" height="16" fill="{c}" stroke="#555" stroke-width="0.8"/>' + _t(66, yy + 13, txt, 13))
    mk = '<marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#222"/></marker>'
    return _svg(W, H, body, defs + mk)


def _pos(sec, name, nth=0):
    x, n = 0.0, 0
    for nm, w, _ in sec:
        if nm == name:
            if n == nth:
                return x, x + w
            n += 1
        x += w
    raise KeyError(name)


def sections_svg(cfg, res):
    s, secs, e = 30.0, cfg["sections"], cfg["energy"]
    W, H = 1180, 1100
    body = [_t(30, 36, "AEQUCITY v2.0 | CORRIDOR SECTIONS (to scale 1:1, ground line = 0.00) | SCHEMATIC S-02", 18, "start", "#222", "bold")]

    def section(title, key, x0, yg, extras):
        sec = secs[key]
        tot = sum(w for _, w, _ in sec)
        body.append(_t(x0, yg - 215, f"{title}  -  {tot:g} m", 15, "start", "#222", "bold"))
        x = x0
        for nm, w, cls in sec:
            col = COL[cls]
            if nm in ("swale", "verge_swale"):
                body.append(f'<path d="M{x:.1f},{yg} L{x + w * s * .15:.1f},{yg + .5 * s} L{x + w * s * .85:.1f},{yg + .5 * s} L{x + w * s:.1f},{yg} Z" fill="#8fb87a" stroke="#4a7a3a"/>')
                body.append(f'<line x1="{x + w * s * .15:.1f}" y1="{yg + .5 * s}" x2="{x + w * s * .85:.1f}" y2="{yg + .5 * s}" stroke="#3b8fc0" stroke-width="4"/>')
            else:
                body.append(f'<rect x="{x:.1f}" y="{yg}" width="{w * s:.1f}" height="{0.3 * s:.1f}" fill="{col}" stroke="#666" stroke-width="0.6"/>')
            body.append(_t(x + w * s / 2, yg + 2.55 * s + 12, f"{w:g}", 11, "middle", "#333"))
            body.append(_t(x + w * s / 2 - 4, yg + 2.55 * s + 26, nm.replace("_", " "), 10, "end", "#555", "normal", -35))
            x += w * s
        body.append(f'<line x1="{x0 - 10}" y1="{yg}" x2="{x + 10:.1f}" y2="{yg}" stroke="#222" stroke-width="1.5"/>')
        extras(x0, yg, sec)

    def trough(x0, yg, xm, wet=False):
        w, d = (1.2, 1.8) if wet else (1.2, 0.9)
        col, lab = ("#4a90c2", "wet strip") if wet else ("#c9822b", "trough")
        body.append(f'<rect x="{x0 + (xm - w / 2) * s:.1f}" y="{yg + .3 * s}" width="{w * s:.1f}" height="{(d - .3) * s:.1f}" fill="{col}" fill-opacity="0.35" stroke="{col}" stroke-width="2"/>')
        if wet:
            for i, c in enumerate(("#2d6db5", "#8e44ad", "#7b5e3b")):
                body.append(f'<circle cx="{x0 + (xm - .35 + .35 * i) * s:.1f}" cy="{yg + 1.1 * s}" r="{.13 * s:.1f}" fill="{c}"/>')
        else:
            body.append(f'<circle cx="{x0 + (xm - .3) * s:.1f}" cy="{yg + .65 * s}" r="{.12 * s:.1f}" fill="#d4351c"/><circle cx="{x0 + (xm + .1) * s:.1f}" cy="{yg + .65 * s}" r="{.12 * s:.1f}" fill="#2e8b57"/>')

    def tree(x0, yg, xm, r=1.8, h=4.5):
        body.append(f'<line x1="{x0 + xm * s:.1f}" y1="{yg}" x2="{x0 + xm * s:.1f}" y2="{yg - h * s * .6:.1f}" stroke="#6b4a2b" stroke-width="3"/>')
        body.append(f'<circle cx="{x0 + xm * s:.1f}" cy="{yg - h * s * .8:.1f}" r="{r * s:.1f}" fill="#5f9e4f" fill-opacity="0.75"/>')

    def seam_ex(x0, yg, sec):
        a, b = _pos(sec, "forest_verge", 0)
        tree(x0, yg, (a + b) / 2)
        a, b = _pos(sec, "forest_verge", 1)
        tree(x0, yg, (a + b) / 2)
        t0, t1 = _pos(sec, "walk", 0)
        trough(x0, yg, (t0 + t1) / 2)
        w0, w1 = _pos(sec, "slow_street", 0)
        trough(x0, yg, w0 + 0.5, wet=True)
        t0, t1 = _pos(sec, "walk", 1)
        trough(x0, yg, (t0 + t1) / 2)
        w0, w1 = _pos(sec, "slow_street", 1)
        trough(x0, yg, w1 - 0.5, wet=True)
        c0, c1 = _pos(sec, "colonnade_zone")
        k0, k1 = _pos(sec, "cycle_track")
        cw = e["canopy_width_m"]
        xc = (c0 + c1) / 2
        body.append(f'<line x1="{x0 + xc * s:.1f}" y1="{yg}" x2="{x0 + xc * s:.1f}" y2="{yg - 4.5 * s:.1f}" stroke="#444" stroke-width="5"/>')
        xl, xr = xc - cw + 0.5, xc + 0.5
        body.append(f'<polygon points="{x0 + xl * s:.1f},{yg - 4.5 * s + 6:.1f} {x0 + xr * s:.1f},{yg - 4.5 * s - 6:.1f} {x0 + xr * s:.1f},{yg - 4.5 * s - 14:.1f} {x0 + xl * s:.1f},{yg - 4.5 * s - 2:.1f}" fill="#1f3b73" stroke="#0e1f45"/>')
        body.append(f'<circle cx="{x0 + xc * s:.1f}" cy="{yg - 4.3 * s:.1f}" r="5" fill="#ffb347"/>')
        body.append(_t(x0 + xl * s, yg - 4.5 * s - 24, f"PV colonnade {cw:g} m + luminaire (amber <=2200 K)", 11))
        s0, s1 = _pos(sec, "swale")
        body.append(_t(x0 + (s0 + s1) / 2 * s, yg + 1.0 * s + 6, "swale", 10, "middle", "#2b6a8f"))
        body.append(_t(x0, yg + 215, "TROUGH 1.2 x 0.9 m (under each walk): LV power + fibre microducts + 100% spare ducts, lockable IP-rated lids", 12, "start", "#9a5a10"))
        body.append(_t(x0, yg + 236, "WET STRIP 1.2 x 1.8 m (street service band, liftable pavers): potable | non-potable | sewer; storm = surface swale, no pipe", 12, "start", "#2d6db5"))

    def lane_ex(x0, yg, sec):
        for i in (0, 1):
            a, b = _pos(sec, "verge_swale", i)
            tree(x0, yg, (a + b) / 2 + (0.0), r=1.5, h=4.0)
        a, b = _pos(sec, "footpath")
        trough(x0, yg, (a + b) / 2)
        c0, c1 = _pos(sec, "carriageway")
        trough(x0, yg, c1 - 0.7, wet=True)
        body.append(_t(x0, yg - 5.4 * s, "shared surface 4.5 m: >=4.0 m clear (emergency >=3.7 m)", 12))

    def path_ex(x0, yg, sec):
        for i in (0, 1):
            a, b = _pos(sec, "verge")
            tree(x0, yg, 0.75 if i == 0 else 5.25, r=1.0, h=3.2)

    section("S-CLASS SEAM (AEQUSPINE) between cells", "seam", 60, 310, seam_ex)
    section("L-CLASS LANE (within cell)", "lane", 60, 790, lane_ex)
    section("P-CLASS PATH (pedestrian / cycle)", "path", 600, 790, path_ex)
    body.append(_t(60, 1030, "Rules: potable above sewer, >=0.3 m vertical / >=1.0 m horizontal separation | trees never above wet strip (root barriers) | LV only in trough | lids IP-rated + lockable", 12))
    body.append(_t(60, 1052, "Surfaces: permeable interlocking pavers (street), liftable pavers (walk/service band), smooth stone/geopolymer ribbons (cycle track), tactile guidance strip on walks (ISO 23599)", 12))
    return _svg(W, H, body)


def metabolism_svg(cfg, res):
    m = res["metabolism"]
    W, H = 1300, 760
    body = [_t(30, 36, "AEQUCITY v2.0 | CELL METABOLISM (per capita per year) | SCHEMATIC S-03", 18, "start", "#222", "bold")]

    def box(x, y, w, h, title, lines, col):
        body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{col}" stroke="#555" stroke-width="1.2"/>')
        body.append(_t(x + w / 2, y + 20, title, 14, "middle", "#111", "bold"))
        for i, ln in enumerate(lines):
            body.append(_t(x + w / 2, y + 40 + i * 16, ln, 12, "middle", "#222"))

    def arrow(x1, y1, x2, y2, label=""):
        body.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#444" stroke-width="2" marker-end="url(#ar)"/>')
        if label:
            body.append(_t((x1 + x2) / 2, (y1 + y2) / 2 - 6, label, 11, "middle", "#333"))
    w, e, n, wa, f = m["water_m3_pp"], m["energy_kwh_pp"], m["nutrients_kg_pp"], m["waste_kg_pp"], m["food_kg_pp"]
    box(30, 80, 220, 90, "RAIN + WEDGE RUNOFF", [f"{w['rain_on_cell']:.1f} m3 on cell", "roofs | permeable | swales"], "#d6ecf7")
    box(330, 80, 240, 90, "TANKS | PONDS | MAR", ["storage + managed recharge", "floating PV on ponds"], "#bfe0f1")
    ext = res["water"]["ext_m3_pp"]
    box(650, 80, 240, 90, "POTABLE (treated)", [f"{w['potable']:.1f} m3 | external {ext['pot']:.1f} m3"], "#cde8f6")
    box(970, 80, 280, 90, "RECLAIMED LOOP", [f"greywater {w['grey_reclaimed_yr']:.1f} m3 + effluent", f"irrigation {w['irrigation']:.1f} m3 (external {ext['irr']:.1f})"], "#dff0df")
    arrow(250, 125, 330, 125, "harvest"); arrow(570, 125, 650, 125, "treat"); arrow(890, 125, 970, 125, "reuse")
    box(30, 300, 220, 100, "SUN", [f"{e['generation']:.0f} kWh PV", "roofs | canopy | agri-PV | ponds"], "#fff1c9")
    box(330, 300, 240, 100, "HOME NODES + CELL GRID", [f"demand {e['demand']:.0f} kWh", "battery + smart control"], "#ffe49a")
    box(650, 300, 240, 100, "BIOGAS CHP", [f"{e['chp']:.0f} kWh_e", "from organics + blackwater"], "#f6d7a8")
    box(970, 300, 280, 100, "GRID OUT / IN", [f"export {e['export']:.0f} kWh", f"import {e['import']:.0f} kWh"], "#ffd27a")
    arrow(250, 350, 330, 350); arrow(650, 350, 570, 350); arrow(570, 380, 970, 380, "feed excess outward")
    box(30, 530, 280, 100, "FOOD + AGRI", [f"{f['local_produced']:.0f} kg local of {f['diet']:.0f} kg diet", "productive landscape + ward belt"], "#d9eec3")
    box(400, 530, 260, 100, "NUTRIENT LOOP", [f"N {n['supply_NPK'][0]:.1f} P {n['supply_NPK'][1]:.2f} K {n['supply_NPK'][2]:.2f} kg", "recovered excreta"], "#e8d9c0")
    box(740, 530, 240, 100, "WASTE", [f"{wa['generated']:.0f} kg gen | {wa['recovered']:.0f} kg recovered", f"residual {wa['residual']:.1f} kg"], "#e6e6e6")
    box(1060, 530, 190, 100, "DATA MESH", ["sensors on every loop", "local-first, open"], "#e3dcf0")
    body.append('<path d="M1250,125 H1278 V470 H170 V530" fill="none" stroke="#444" stroke-width="2" marker-end="url(#ar)"/>'); body.append(_t(700, 462, "irrigation + nutrients to productive landscape", 11, "middle", "#333")); arrow(660, 580, 740, 580); arrow(400, 580, 310, 580)
    mk = '<marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#444"/></marker>'
    return _svg(W, H, body, mk)


def draw_all(cfg, res, outdir):
    import pathlib
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    files = {"S-01_ward_plan.svg": ward_plan_svg, "S-02_corridor_sections.svg": sections_svg, "S-03_cell_metabolism.svg": metabolism_svg}
    for name, fn in files.items():
        (out / name).write_text(fn(cfg, res), encoding="utf-8")
    return sorted(files)
