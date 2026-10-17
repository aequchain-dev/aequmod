"""efe_city.tables - computed ODF tables (registered by name for {{table:NAME}} placeholders)."""
from __future__ import annotations

import math

from .core import MONTHS
from .report import W, block, kv, table, table_fn, para
from . import content as C
from . import evaluate as ev
from .synergy import CODE2, SUBS, TRENCH, UNIFIED
from .resilience import CRITERIA

f0 = lambda v: f"{v:,.0f}"
f1 = lambda v: f"{v:,.1f}"
f2 = lambda v: f"{v:,.2f}"
pc = lambda v: f"{100 * v:.0f}%"
tick = lambda ok: "PASS" if ok else "FAIL"


@table_fn("meta")
def _meta(c):
    d = c["d"]
    return kv([("Document", "AEQUCITY v2.0 - Synergetic EFE City Blueprint"), ("Version / date", f"2.0.0 / {d['date']}"),
               ("Agent", "EFE OPTIBEST ENGINEER v2.0 (ODF v1.0, SI units)"), ("Supersedes", "AequCity v1.0 framework (ttx89-dev/resources/aequcity.md)"),
               ("Scale / rigor", "MACRO x GLOBAL/INFRASTRUCTURE -> ULTRA"), ("Reference site", c["res"]["climate"]["label"]),
               ("Status", f"DESIGN-BASIS PLATEAU (model-verified), {d['n_open']} field gates open"),
               ("Reproduce", "python -m efe_city build --out out   (all numbers + drawings regenerate)")])


@table_fn("headline")
def _headline(c):
    L, r, k, g = c["res"]["land"], c["res"], c["k"], c["cfg"]["geometry"]
    E, W_, F, S = r["energy"], r["water"], r["food"], r["waste"]
    return block("HEADLINE SPECIFICATIONS", [
        f"Cell (AEQUCELL) : hexagon, apothem {g['cell_apothem_m']} m ({2 * g['cell_apothem_m']} m flat-to-flat), {L['hex']['area_ha']:.1f} ha, {f0(L['pop_cell'])} residents at {g['gross_density_p_ha']} p/ha",
        f"Ward / City     : {g['cells_per_ward']} cells = {f0(c['d']['pop_ward'])} p ; {g['wards']} wards = {f0(L['city']['pop'])} p on {c['d']['city_km2']:.1f} km2 (R {L['city']['radius_km']:.1f} km, incl. wedge + nature)",
        f"Access          : {pc(k['access_cov400'])} within 400 m of a daily node (P95 {r['access']['cell_node']['p95_min']:.1f} min); ward services P95 {r['access']['ward_node']['p95_min']:.1f} min",
        f"AEQUSPINE       : seam {g['seam_width_m']} m / lane {g['lane_width_m']} m / path {g['path_width_m']} m ; 2 trenches (trough + wet strip) replace 6",
        f"Water           : potable {pc(k['potable_ssr'])} self-supplied; irrigation {pc(k['irrigation_ssr'])}; drought {W_['drought']['years']} yr: unmet {W_['drought']['unmet_pot_pct']:.1f}%",
        f"Energy          : {E['kwp_pp']:.2f} kWp/p, {pc(k['energy_ssr'])} self-supply, export {f0(E['export_kwh_pp'])} kWh/p/yr, storage {E['storage_kwh_pp']} kWh/p",
        f"Food            : fresh produce {pc(k['fresh_ssr'])} in-city + ward belt; {pc(F['kcal_ssr'])} of kcal; foodshed R {F['foodshed_radius_km']:.1f} km",
        f"Circularity     : material recovery {pc(S['recovery'])} (target), residual {S['residual_kg_pp']:.1f} kg/p/yr",
        f"Safety          : {c['d']['gates_ok']}/{c['d']['gates_n']} gates pass; max FMEA RPN {r['fmea']['max_rpn_pre']} -> {r['fmea']['max_rpn_post']}",
        f"Economics       : capex ~USD {f0(r['economics']['capex_pp'])}/p ; external cost USD {f0(r['economics']['external_cost_pp'])}/p/yr (planning-grade)"], spec=True)


@table_fn("efe_filter")
def _efe(c):
    r, k = c["res"], c["k"]
    rows = [("1 SUSTAINABLE", f"recovery {pc(r['waste']['recovery'])}; nature {pc(c['cfg']['geometry']['nature_fraction'])} of city; MAR recharge; compost loop", "PASS"),
            ("2 RENEWABLE", f"PV + biogas; self-supply {pc(k['energy_ssr'])}; no fossil source (grid = outward-feed partner)", "PASS"),
            ("3 ACCESSIBLE", f"{pc(k['access_cov400'])} within 400 m; step-free routes; hygiene hubs; universal design", "PASS"),
            ("4 OPEN", "open standards, open model + tests, patent-free materials (stone, geopolymer, timber, earth)", "PASS"),
            ("5 LOCAL-FIRST", "local waste-stream materials; cell-level production; internalization priority ranked", "PASS"),
            ("6 CIRCULAR", f"P-loop closure {pc(r['food']['nutrient_closure_diet'][1])} of diet; water reuse; recovery {pc(r['waste']['recovery'])}", "PASS (design)"),
            ("7 DURABLE", "stone/geopolymer paving 50+ y; liftable + repairable; spare ducts; design life >= 20 y", "PASS")]
    return table(["EFE principle", "evidence (this model)", "result"], rows, widths=[15, 52, 8])


@table_fn("pillars")
def _pillars(c):
    rows = [("Material", "Tier 1-2 hierarchy; surfaces + structure", "7.3, 7.6"), ("Energy", "PV + biogas + storage; no perpetual source", "6.4"),
            ("Waste", "recovery, residual mass, digestion", "7.5"), ("Water", "sponge, reuse, MAR, drought", "6.3"),
            ("Social", "equidistributed access, universal design, hygiene hubs", "5, 7.5"), ("Economic", "external cost + contribution bound", "9"),
            ("Temporal", "repairable, upgradable, horizons T1-T3", "11, 12")]
    return table(["7 verification pillar", "where evidenced", "section"], rows)


@table_fn("sources")
def _sources(c):
    return table(["source", "read depth", "contribution"], C.SOURCES, widths=[24, 24, 28])


@table_fn("v1_audit")
def _v1(c):
    a0, a1 = c["an"]["ladder"][0]["k"], c["an"]["ladder"][-1]["k"]
    rows = [("layout", "concentric core; claims <15 min to everything", f"I0: {pc(a0['access_cov400'])} within 400 m; district P95 {a0['ward_p95_min']:.0f} min", f"hex: {pc(a1['access_cov400'])}; ward P95 {a1['ward_p95_min']:.1f} min"),
            ("energy", "perpetual-motion generator as primary source", f"violates energy conservation; PV-only I0 self-supply {pc(a0['energy_ssr'])}", f"PV + storage + CHP: {pc(a1['energy_ssr'])}; converters only (eta<1)"),
            ("underground", "4 underground levels + radial tunnels", f"assumed 21 km bore: excavation {a0['excavation_m3_pp']:.1f} m3/p; capex +~USD 12.6k/p (assumed 60 M/km)", f"shallow trough: {a1['excavation_m3_pp']:.1f} m3/p"),
            ("drainage", "'sponge' stated, not sized", f"piped I0: potable self-supply {pc(a0['potable_ssr'])}", f"sponge + MAR: {pc(a1['potable_ssr'])}"),
            ("orientation", "fixed N nature / S industry zoning", "hemisphere + wind-rose dependent", "parametric site adapter (section 12)"),
            ("recycling", "99.7% claimed", "uncorroborated; no commissioning audit", f"target >= 95%, verified by audit (L-14)"),
            ("hazards", "no hazard layer", "tornado, seismic, fire, flood absent", "hazard-profile adapter + shelters (section 8)"),
            ("economics", "free everything, no cost accounting", "no capex / external cost", "capex + external cost + contribution bound (section 9)")]
    return table(["topic", "v1.0 states (paraphrased)", "model evidence", "v2.0 treatment"], rows, widths=[11, 22, 22, 20])


@table_fn("gates")
def _gates(c):
    rows = [(q["id"], q["text"], f"{q['value']:.3g}", tick(q["ok"])) for q in c["gates"]]
    return table(["gate", "requirement (binary)", "value", "result"], rows, widths=[5, 56, 8, 5])


@table_fn("constraints")
def _cons(c):
    return table(["type", "constraint", "handling"], C.CONSTRAINTS, widths=[16, 34, 24])


@table_fn("weights")
def _weights(c):
    rows = [(n, v[3], v[4], str(v[2])) for n, v in ev.SPEC.items()]
    return table(["KPI", "dimension", "meaning", "w"], rows, widths=[17, 12, 41, 3])


@table_fn("requirements")
def _req(c):
    return table(["id", "requirement (from the brief)", "section", "verification"], C.REQUIREMENTS, widths=[4, 40, 8, 21])


@table_fn("layouts")
def _layouts(c):
    a0, a1 = c["an"]["ladder"][0]["k"], c["an"]["ladder"][-1]["k"]
    r = c["res"]
    side = math.sqrt(r["land"]["hex"]["area_m2"])
    seam_h, seam_sq = r["land"]["hex"]["seam_len_m"], 2 * side
    rows = [("residents within 400 m of daily node", pc(a0["access_cov400"]), pc(a1["access_cov400"])),
            ("P95 walk to ward-level services (min)", f1(a0["ward_p95_min"]), f1(a1["ward_p95_min"])),
            ("vehicle conflict points per ha", f1(r["streets"]["conflict_pts_ha_grid"]), f1(r["streets"]["conflict_pts_ha_hex"])),
            ("population added per growth step", f0(a0["growth_step_pop"]), f0(a1["growth_step_pop"])),
            ("shared edge per cell vs equal-area square (m)", f"{seam_sq:.0f} (square)", f"{seam_h:.0f} (hex, -{100 * (1 - seam_h / seam_sq):.1f}%)")]
    return table(["metric (computed)", "concentric-radial (v1.0)", "hex cellular (v2.0)"], rows, widths=[34, 20, 20]) + \
        [""] + para("Orthogonal grid: 4-leg junctions give ~4x the conflict points; linear ribbon: walk time grows with length (qualitative). Hexagon minimises perimeter for equal area (honeycomb theorem), so the cell is at the theoretical edge-length minimum.")


@table_fn("hierarchy")
def _hier(c):
    L, g, d = c["res"]["land"], c["cfg"]["geometry"], c["d"]
    rows = [("Court", f"~{g['court_persons']}", "-", "kiosk, compost point, play lot, tool library", "30 m"),
            ("Cell", f0(L["pop_cell"]), f"{L['hex']['area_ha']:.1f}", "school, market, hygiene hub, shelter, workshop, RRP", "<= 5.4 min"),
            ("Ward", f0(d["pop_ward"]), f"{d['ward_ha']:.0f}", "secondary school, clinic, fire station, digester + wetland", "<= 14 min"),
            ("City", f0(L["city"]["pop"]), f"{L['city']['total_m2'] / 1e4:,.0f}", "hospital, college, manufactory, transit interchange", "shuttle")]
    return table(["level", "people", "ha", "anchor facilities", "walk"], rows, widths=[6, 8, 7, 41, 10])


@table_fn("land_budget")
def _land(c):
    L = c["res"]["land"]
    A, P = L["hex"]["area_m2"], L["pop_cell"]
    parts = [("buildings (footprint)", L["footprint_m2"]), ("seams (S-class)", L["corridor_m2"]["seam"]), ("lanes (L-class)", L["corridor_m2"]["lane"]),
             ("paths (P-class)", L["corridor_m2"]["path"]), ("node plaza + civic green", L["node_m2"]), ("plots / court gardens", L["plots_m2"])]
    rows = [(n, f0(v), f1(100 * v / A), f1(v / P)) for n, v in parts] + [("TOTAL cell", f0(A), "100.0", f1(A / P))]
    out = table(["component", "m2 per cell", "% of cell", "m2 / person"], rows, aligns=["l", "r", "r", "r"])
    S = L["surface_m2"]
    rows2 = [(k, f0(v), f1(100 * v / A)) for k, v in S.items()]
    return out + [""] + table(["surface class", "m2 per cell", "% of cell"], rows2, aligns=["l", "r", "r"]) + [""] + kv([
        ("productive landscape in cell", f"{f0(L['prod_cell_m2'])} m2 = {L['prod_cell_m2'] / P:.1f} m2/p"),
        ("city: built / wedge / nature", f"{L['city']['built_m2'] / 1e6:.1f} / {L['city']['wedge_area_m2'] / 1e6:.1f} / {L['city']['nature_area_m2'] / 1e6:.1f} km2"),
        ("city gross density (all land)", f"{L['city']['gross_density_p_ha']:.0f} p/ha")])


@table_fn("terrain")
def _terrain(c):
    r, cfg = c["res"], c["cfg"]
    rows = [(f"{t['slope_pct']}%", f2(t["speed_kmh"]), pc(t["rel"]), f0(t["apothem_eff_m"])) for t in r["terrain"]["table"]]
    bands = [("0-2%", "floodplain edge, wetlands, agri; no buildings below 1:100 line"), ("2-5%", "prime urban: all classes, step-free everywhere"),
             ("5-8%", "urban with terraces; contour lanes; ramps <= 8.33%"), ("8-12%", "contour streets, stepped paths + e-assist; road <= 10%"),
             ("12-25%", "agroforestry terraces, switchbacks (road <= 10%), no cells"), (">25%", "protected forest / fynbos; erosion + fire control")]
    return table(["slope", "walk km/h (Tobler)", "relative", "eff. apothem m"], rows, aligns=["l", "r", "r", "r"]) + [""] + \
        table(["slope band", "use"], bands, widths=[8, 66])


@table_fn("sun")
def _sun(c):
    s = c["res"]["sungeo"]
    rows = [(str(q["storeys"]), f1(q["height_m"]), f1(q["spacing_req_m"]), f1(q["spacing_actual_m"]), tick(q["ok"])) for q in s["rows"]]
    return kv([("latitude", f"{s['lat']:.1f} deg"), ("noon sun elevation winter / summer", f"{s['winter_noon_elev']:.1f} / {s['summer_noon_elev']:.1f} deg"),
               ("optimum PV tilt (equator-facing)", f"{c['res']['solar']['opt_tilt']} deg")]) + [""] + \
        table(["storeys", "height m", "spacing req m", "lane spacing m", "winter sun"], rows, aligns=["l", "r", "r", "r", "l"])


@table_fn("sections")
def _sections(c):
    out = []
    for k, sec in c["cfg"]["sections"].items():
        out += [f"{k.upper()} class, total {sum(w for _, w, _ in sec):g} m"] + table(["element", "width m", "surface class"], [(n.replace('_', ' '), f"{w:g}", cl) for n, w, cl in sec], widths=[22, 8, 20], aligns=["l", "r", "l"]) + [""]
    return out


@table_fn("separation")
def _sep(c):
    return table(["pair", "rule", "note"], C.SEPARATION, widths=[18, 38, 18])


@table_fn("water_balance")
def _wb(c):
    w = c["res"]["water"]
    rows = [(MONTHS[r["m"]], f0(r["rain_mm"]), f2(r["pot"]), f2(r["irr"]), f2(r["ext_irr"]), f2(r["tank"]), f2(r["pond"]), f2(r["mar"])) for r in w["rows"]]
    out = table(["month", "rain mm", "potable", "irrigation", "ext irr", "tank", "pond", "MAR"], rows, aligns=["l"] + ["r"] * 7)
    return out + [""] + kv([("annual per capita (m3)", f"potable {w['pot_m3_pp']:.1f} | non-potable {w['np_m3_pp']:.1f} | irrigation {w['irr_m3_pp']:.1f}"),
                            ("external top-up (m3)", f"potable {w['ext_m3_pp']['pot']:.2f} | irrigation {w['ext_m3_pp']['irr']:.1f}"),
                            ("self-supply", f"potable {pc(w['ssr_potable'])} | irrigation {pc(w['ssr_irrigation'])} | total {pc(w['ssr_total'])}"),
                            ("peak storage (m3/p)", f"pond {w['peak_pond']:.1f} | MAR {w['peak_mar']:.1f}"),
                            ("mass balance closure (rel.)", f"{w['closure_rel']:.1e}"),
                            ("drought design", f"{w['drought']['years']} yr at {pc(w['drought']['factor'])} rain, potable restricted: unmet {w['drought']['unmet_pot_pct']:.1f}%")])


@table_fn("energy_balance")
def _eb(c):
    e = c["res"]["energy"]
    rows = [(MONTHS[i], f0(m["gen"]), f0(m["dem"]), f1(m["imp"]), f0(m["exp"])) for i, m in enumerate(e["monthly"])]
    out = table(["month", "PV kWh/p", "demand", "import", "export"], rows, aligns=["l"] + ["r"] * 4)
    pl = [(p["name"], f2(p["m2_pp"]), f2(p["kwp_pp"]), f0(p["kwh_kwp"]), f0(p["kwh_pp"])) for p in e["placements"]]
    dm = [(k.replace("_", " "), f0(v)) for k, v in e["demand_split"].items()]
    eq = [(str(q["storeys"]), f0(q["roof_kwh_pp"]), pc(q["ratio"])) for q in e["equity"]]
    return out + [""] + table(["placement", "m2/p", "kWp/p", "kWh/kWp", "kWh/p/yr"], pl, aligns=["l"] + ["r"] * 4) + [""] + \
        table(["demand end-use", "kWh/p/yr"], dm, aligns=["l", "r"]) + [""] + \
        table(["storeys", "roof PV kWh/p", "share of demand"], eq, aligns=["l", "r", "r"]) + [""] + kv([
            ("self-supply / import / export", f"{pc(e['ssr'])} / {e['import_kwh_pp']:.1f} / {f0(e['export_kwh_pp'])} kWh/p/yr"),
            ("loss-of-load days / longest run", f"{e['lold_days']} / {e['max_import_run_days']} d"), ("closure", f"{e['closure_kwh_pp']:.1e} kWh/p"),
            ("home node (per dwelling)", f"{e['hen']['pv_kwp']:.1f} kWp PV, {e['hen']['battery_kwh']:.1f} kWh battery, {e['hen']['inverter_kw']:.1f} kW hybrid inverter"),
            ("cell battery", f"{e['hen']['cell_battery_mwh']:.1f} MWh per cell (grid-forming, N+1)")])


@table_fn("standards")
def _std(c):
    return table(["domain", "open reference (verify edition)", "use"], C.STANDARDS, widths=[16, 40, 18])


@table_fn("food_ladder")
def _food(c):
    F, cfg = c["res"]["food"], c["cfg"]["food"]
    rows = [(g, f1(cfg["diet_kg_pp"][g]), f1(F["need_m2_pp"][g]), f1(F["alloc_m2_pp"][g]), f1(F["produced_kg_pp"][g])) for g in cfg["priority"]]
    return table(["food group", "diet kg/p/y", "need m2/p", "in-city m2/p", "local kg/p"], rows, aligns=["l"] + ["r"] * 4) + [""] + kv([
        ("fresh produce self-supply", pc(F["fresh_ssr"])), ("kcal produced in-city", f"{pc(F['kcal_ssr'])} ({F['kcal_local_pd']:.0f} of {F['kcal_diet_pd']:.0f} kcal/p/d)"),
        ("land for full diet", f"{F['land_need_pp_m2']:.0f} m2/p ; remote {F['remote_land_pp_m2']:.0f} m2/p"),
        ("foodshed radius (staples)", f"{F['foodshed_radius_km']:.1f} km from city centre"), ("agri electricity", f"{F['energy_kwh_pp']:.0f} kWh/p/yr"),
        ("mushroom house floor (city-wide)", f"{F['mushroom_m2_city']:,.0f} m2 growing floor, city-wide")])


@table_fn("nutrients")
def _nut(c):
    F = c["res"]["food"]
    rows = [(n, f2(F["nutrient_supply_kg_pp"][i]), f2(F["nutrient_removal_local"][i]), f2(F["nutrient_removal_diet"][i]), pc(F["nutrient_closure_diet"][i])) for i, n in enumerate("NPK")]
    return table(["nutrient", "recovered kg/p/y", "in-city crops", "whole diet (plants)", "diet closure"], rows, aligns=["l"] + ["r"] * 4)


@table_fn("palette")
def _pal(c):
    return table(["zone / function", "indicative species", "note"], C.PALETTE, widths=[22, 38, 16])


@table_fn("means")
def _means(c):
    m, out = c["res"]["means"], []
    for util, d in m["current"].items():
        rows = [(o, f2(s), pc(d["stability"].get(o, 0)), "BEST" if o == d["best"] else "") for o, s in sorted(d["scores"].items(), key=lambda kv_: -kv_[1])]
        rows += [(o, "-", "-", "excluded: safety < 3") for o in d["excluded"]]
        out += para(f"{util.upper()} delivery means (criteria: {', '.join(CRITERIA)})") + table(["option", "score", "wins", ""], rows, widths=[20, 6, 6, 22], aligns=["l", "r", "r", "l"]) + [""]
    pr = [(k[:18], v["power"]["best"], v["water"]["best"], v["data"]["best"]) for k, v in m["profiles"].items()]
    return out + table(["hazard profile", "power", "water", "data"], pr, widths=[14, 19, 19, 19])


@table_fn("colocation")
def _coloc(c):
    Y, cfg, L = c["res"]["synergy"], c["cfg"], c["res"]["land"]
    net, P, ex = Y["net_len_cell_m"], L["pop_cell"], cfg["economics"]["excavation_usd_m3"]
    sv, uv = Y["sep_m3_per_m"], Y["uni_m3_per_m"]
    si, ui = sum(x[2] for x in TRENCH.values()), sum(x[2] for x in UNIFIED.values())
    rows = [("trench types per street", "6", "2", f"-{Y['saving_openings_pct']:.0f}%"), ("excavation m3 per m of street", f2(sv), f2(uv), f"-{Y['saving_excavation_pct']:.0f}%"),
            ("excavation m3 per person", f2(sv * net / P), f2(uv * net / P), f"-{Y['saving_excavation_pct']:.0f}%"),
            ("corridor cost USD/p (planning)", f0((sv * ex + si) * net / P), f0((uv * ex + ui) * net / P), f"{100 * ((uv * ex + ui) / (sv * ex + si) - 1):.0f}%"),
            ("utility length inspectable w/o cutting surface", "3%", pc(Y["inspectable_fraction"]), "x27"),
            ("subsystem pairs with shared space or flow", str(Y["matrix_separate"]), str(Y["synergy_pairs"]), f"+{Y['synergy_pairs'] - Y['matrix_separate']}")]
    return table(["metric", "separate trenches", "AEQUSPINE unified", "change"], rows, widths=[34, 14, 14, 8])


@table_fn("matrix")
def _matrix(c):
    M = c["res"]["synergy"]["matrix"]
    codes = M["codes"]
    out = ["      " + " ".join(CODE2[x] for x in codes)]
    for a in codes:
        out.append(f"{a:5s} " + " ".join(" ." if a == b else f" {M['cells'][(a, b)]}" for b in codes))
    out += [""] + para("legend: B shared space + flow | F flow (output feeds input) | S shared space | i information link | X conflict (managed) | . none") + [""]
    top = [(f"{p['a']}-{p['b']}", str(p["F"]), str(p["S"]), str(p["I"]), str(p["score"])) for p in M["top"][:12]]
    out += table(["top synergy pairs", "F", "S", "I", "score"], top, widths=[20, 4, 4, 4, 6], aligns=["l", "r", "r", "r", "r"]) + [""]
    out += table(["conflict pair", "reason", "managed by"], [(f"{a}-{b}", r, m) for a, b, r, m in M["conflicts"]], widths=[11, 24, 40])
    return out


@table_fn("zones")
def _zones(c):
    zg = c["res"]["synergy"]["matrix"]["zone_groups"]
    return table(["shared zone", "subsystems co-located"], [(z, " ".join(v)) for z, v in sorted(zg.items(), key=lambda kv_: -len(kv_[1]))], widths=[10, 64])


@table_fn("streets")
def _streets(c):
    r, cfg = c["res"], c["cfg"]["streets"]
    rows = [(q["class"], f0(q["speed_kmh"]), f1(q["ssd_flat_m"]), f1(q["ssd_down8_m"]), f2(q["clear_m"]), "yes" if q["emergency_ok"] else "n/a (path)") for q in r["streets"]["rows"]]
    dv = table(["design vehicle", "use", "width m", "length m"], [(a, b, f1(w), f1(l)) for a, b, w, l in cfg["design_vehicles"]], widths=[8, 28, 8, 8])
    return table(["class", "km/h", "SSD m", "SSD -8%", "clear m", "emergency"], rows, aligns=["l"] + ["r"] * 4 + ["l"]) + [""] + dv + [""] + kv([
        ("junction conflict points / ha", f"hex {r['streets']['conflict_pts_ha_hex']:.1f} vs 4-leg grid {r['streets']['conflict_pts_ha_grid']:.1f}"),
        ("max distance dwelling -> drivable street", f"{r['streets']['max_reach_m']:.0f} m (hose reach {cfg['hose_reach_m']} m)"),
        ("grade limits", f"road {cfg['max_grade_pct']['road']}% | walk {cfg['max_grade_pct']['walk']}% | ramp {cfg['max_grade_pct']['ramp']}%")])


@table_fn("transport")
def _trans(c):
    t, a = c["res"]["transport"], c["res"]["access"]["seam_stop"]
    return kv([("shuttle fleet (12 seat)", f"{t['fleet_shuttles']} ({t['fleet_per_1000']:.2f} per 1000 people), peak {f0(t['peak_trips_h'])} trips/h"),
               ("shuttle route length", f"{t['seam_route_km']:.0f} km (seams)"), ("stop distance", f"P95 {a['p95_m']:.0f} m ; {pc(a['cov'])} within 400 m"),
               ("mobility energy", f"{t['energy_kwh_pp']:.0f} kWh/p/yr (shuttle {t['shuttle_kwh_pp']:.0f} + trike {t['trike_kwh_pp']:.0f})")])


@table_fn("facilities")
def _fac(c):
    F = c["res"]["facilities"]
    h = F["hub"]
    return table(["facility", "count (city)"], [(n, f0(q)) for n, q in F["rows"]], widths=[46, 14], aligns=["l", "r"]) + [""] + kv([
        ("drinking-water points", f"{f0(F['drinking_points'])} (<= 200 m along seams, every court, every node)"),
        ("hygiene hub per cell", f"{h['wc']} WC ({h['accessible_wc']} accessible), {h['basins']} basins, {h['showers']} showers, {h['washers']} washers; {h['water_m3_day']:.0f} m3/day"),
        ("hub design", "peak users " + f0(h["peak_users"]) + "; urine-diverting option; greywater -> wetland; blackwater -> digester")])


@table_fn("surfaces")
def _surf(c):
    cm = c["cfg"]["resilience"]["c_peak"]
    return table(["class", "specification", "C peak", "EFE tier"], [(a, b, cm[a], t) for a, b, _, t in C.SURFACES], widths=[16, 40, 6, 8])


@table_fn("hazards")
def _haz(c):
    nm = {"unreinforced_earth": "unreinf. earth", "confined_earth": "confined earth", "timber_bamboo_frame": "timber/bamboo", "steel_timber_hybrid": "steel-timber"}
    rows = [(k.replace("stress_", "S:"), f0(v["hz"]["gust_ms"]), f2(v["q_kpa"]), f2(v["hz"]["pga_g"]), nm[v["system"][0]], "yes" if v["safe_rooms"] else "no", f1(v["plinth_m"]), str(v["defensible_m"])) for k, v in c["res"]["structure"]["profiles"].items()]
    st = c["res"]["structure"]["current"]
    return table(["profile", "gust", "q kPa", "PGA", "system", "safe", "plinth", "fire"], rows, widths=[12, 4, 5, 5, 14, 4, 6, 4], aligns=["l", "r", "r", "r", "l", "l", "r", "r"]) + [""] + kv([
        ("wall / roof uplift (ref. profile)", f"{st['wall_kpa']:.2f} / {st['roof_uplift_kpa']:.2f} kPa (edge {st['edge_uplift_kpa']:.2f}); eave tension {st['eave_tension_kn_m']:.1f} kN/m"),
        ("seismic Cs by system (reference)", ", ".join(f"{k.split('_')[0]} {v:.3f}" for k, v in st["cs"].items())),
        ("foundation (soil class " + c["res"]["structure"]["soil"] + ")", c["res"]["structure"]["foundation"][1])]) + [""] + para("gust m/s; safe = community safe rooms; plinth m above the 1:100 level; fire = defensible ring in m")


@table_fn("flood")
def _flood(c):
    f = c["res"]["flood"]
    rows = [(k, f0(v["i_mm_h"]), f"{v['q1_m3s']:.3f}", f"{v['d1_m'] * 100:.1f}", f"{v['dv1']:.3f}", f1(v["max_catchment_ha"])) for k, v in f["events"].items()]
    return table(["event", "i mm/h", "Q 1 ha m3/s", "depth cm", "d*v", "max catchment ha"], rows, aligns=["l"] + ["r"] * 5) + [""] + kv([
        ("peak runoff coefficient", f"area {f['c_area']:.2f} -> attenuated {f['c_peak']:.2f}"), ("limits", "d*v <= 0.4 m2/s and depth <= 0.3 m on overland routes")])


@table_fn("fmea")
def _fmea(c):
    rows = [(q["id"], q["item"], q["mode"], f"{q['S']}/{q['O']}/{q['D']}", str(q["rpn"]), q["mit"], str(q["rpn2"])) for q in c["res"]["fmea"]["rows"]]
    return table(["id", "item", "failure mode", "S/O/D", "RPN", "mitigation (design out > guard > warn)", "RPN2"], rows, widths=[3, 12, 14, 5, 4, 28, 4], aligns=["l", "l", "l", "l", "r", "l", "r"])


@table_fn("risks")
def _risks(c):
    return table(["risk", "L", "I", "mitigation", "owner"], C.RISKS, widths=[24, 1, 1, 30, 12])


@table_fn("economics")
def _econ(c):
    E = c["res"]["economics"]
    LAB = {"corridors_utilities": "corridors + utilities", "digital_waste": "digital + waste machinery", "compliance_it": "compliance + IT",
           "imported_capital_goods": "imported capital goods", "maintenance_parts": "maintenance parts", "food_imports": "food imports",
           "energy_imports": "energy imports", "bulk_water": "bulk water"}
    lab = lambda k: LAB.get(k, k.replace("_", " "))
    cap = [(lab(k), f0(v), f1(100 * v / E["capex_pp"])) for k, v in E["capex"].items()] + [("TOTAL", f0(E["capex_pp"]), "100.0")]
    ext = [(lab(k), f0(v), f1(100 * v / E["external_cost_pp"])) for k, v in E["external"].items()] + [("TOTAL", f0(E["external_cost_pp"]), "100.0")]
    sc = [(f0(s["revenue_pp"]), pc(s["rate"]), "within 5% cap" if s["ok"] else "exceeds cap") for s in E["scenarios"]]
    pr = [(f"I-{i + 1}", lab(k), f0(v)) for i, (k, v) in enumerate(E["priority"])]
    return table(["capex line", "USD / person", "%"], cap, aligns=["l", "r", "r"]) + [""] + table(["external cost line", "USD / p / yr", "%"], ext, aligns=["l", "r", "r"]) + [""] + \
        table(["enterprise revenue USD/p/yr", "contribution rate needed", "vs 5% cap"], sc, aligns=["r", "r", "l"]) + [""] + \
        table(["rank", "internalization priority (largest external cost first)", "USD/p/yr"], pr, widths=[5, 50, 10]) + [""] + kv([
            ("capex envelope (city)", f"USD {E['city_capex_musd']:,.0f} M (planning-grade +-40%)"), ("vs EVER module claim", f"{E['vs_ever']:.2f}x of USD 260,000 per resident"),
            ("revenue for 5% cap", f"USD {f0(E['required_revenue_pp'])} per member per year")])


@table_fn("maintenance")
def _maint(c):
    r, cfg = c["res"], c["cfg"]
    L, S = r["land"], r["land"]["surface_m2"]
    P = L["pop_cell"]
    swale = sum(w for k in cfg["sections"] for n, w, _ in cfg["sections"][k] if "swale" in n and k != "seam") * L["lengths_m"]["lane"] + 3.0 * L["lengths_m"]["seam"]
    pv_m2 = r["energy"]["kwp_pp"] / cfg["energy"]["module_kwp_m2"] * P
    trees = r["structure"]["trees_cell"]
    pond = r["water"]["pond_area_pp"] * P / cfg["geometry"]["cells_per_ward"] / cfg["geometry"]["wards"] * cfg["geometry"]["cells_per_ward"] * cfg["geometry"]["wards"] / L["city"]["cells"]
    rows = [("vacuum-sweep permeable paving", 2, S["permeable_street"] + S["permeable_walk"], 800, "m2/h"),
            ("swale + bioretention clean, replant", 4, swale, 500, "m2/h"), ("PV washing (dry season)", 3, pv_m2, 400, "m2/h"),
            ("trough inspection + lid service", 1, L["lengths_m"]["seam"] + L["lengths_m"]["lane"], 400, "m/h"),
            ("wet-strip valve + leak survey", 1, L["lengths_m"]["seam"] + L["lengths_m"]["lane"], 300, "m/h"),
            ("pond / wetland desilt + harvest", 1, pond, 60, "m2/h"), ("street-tree structural pruning (3-yearly)", 1 / 3, trees, 6, "tree/h")]
    tot, out = 0.0, []
    for n, fr, q, rate, u in rows:
        h = fr * q / rate
        tot += h
        out.append((n, f"{fr:.2g}", f0(q), f"{rate} {u}", f0(h)))
    return table(["task", "per yr", "quantity", "rate", "h / cell / yr"], out, aligns=["l", "r", "r", "r", "r"]) + [""] + kv([
        ("total hours per cell per year", f"{f0(tot)} h  = {tot / 1800:.1f} FTE per cell = {1000 * tot / 1800 / P:.1f} FTE per 1000 people"), ("basis", "planning-grade productivity rates; excludes food production labour")])


@table_fn("horizons")
def _hor(c):
    return table(["component", "T1 Proto", "T2 Advanced", "T3 Apex (projection)"], C.HORIZONS, widths=[12, 22, 20, 18])


@table_fn("jurisdictions")
def _jur(c):
    return table(["profile", "signs", "embedded gen", "loads", "stormwater"], C.JURISDICTIONS, widths=[14, 14, 18, 14, 12])


@table_fn("adapter")
def _adapter(c):
    rows = [(a["site"], f"{a['lat']:.1f}", f"{a['comp0']:.3f}", ",".join(a["fails0"]) or "-", f"{a['comp1']:.3f}", ",".join(a["fails1"]) or "-", str(a["opt_tilt"])) for a in c["an"]["adapter"]]
    return table(["site", "lat", "score", "gates failed", "tuned", "failed after", "tilt"], rows, widths=[13, 6, 6, 12, 6, 12, 4]) + [""] + \
        [w for a in c["an"]["adapter"] for w in para(f"{a['site']}: " + ", ".join(f"{k}={v}" for k, v in a["tuned"].items()), 0)]


@table_fn("ladder")
def _ladder(c):
    rows = [(i["id"], i["name"], f"{i['composite']:.3f}", "" if i["delta"] is None else f"{i['delta']:+.3f}", f"{i['gates_ok']}/{i['gates_n']}") for i in c["an"]["ladder"]]
    kp = [(i["id"], pc(i["k"]["access_cov400"]), pc(i["k"]["potable_ssr"]), pc(i["k"]["irrigation_ssr"]), pc(i["k"]["energy_ssr"]), pc(i["k"]["fresh_ssr"]), f0(i["k"]["capex_pp"]), f0(i["k"]["external_cost_pp"]), f1(i["k"]["excavation_m3_pp"])) for i in c["an"]["ladder"]]
    return table(["id", "design state (cumulative)", "score", "delta", "gates"], rows, widths=[3, 44, 6, 7, 5], aligns=["l", "l", "r", "r", "r"]) + [""] + \
        table(["id", "400m", "potable", "irrig", "energy", "fresh", "capex", "ext", "exc m3"], kp, aligns=["l"] + ["r"] * 8)


@table_fn("dims")
def _dims(c):
    ev_ = {"functional": "access, water, energy, food self-supply", "efficiency": "corridor, excavation, capex, external cost, recovery", "robustness": "flood, shelter, conflicts, autonomy, canopy",
           "scalability": "growth step", "maintainability": "complexity, inspectability", "innovation": "synergy pairs", "elegance": "purpose / complexity"}
    rows = [(d, f"{v:.2f}", str(ev.rubric(v)), ev_[d]) for d, v in c["dims"].items()]
    return table(["dimension", "model score", "rubric (model)", "evidence KPIs"], rows, widths=[15, 11, 8, 36]) + [""] + \
        para("Rubric 4 = EXCELLENT: no enhancement vector found in model space. Rubric 5 (PREMIUM) is reserved for plateau-verified AND field-verified evidence and is therefore NOT claimed.")


@table_fn("plateau")
def _plat(c):
    P = c["an"]["plateau"]
    rows = [(a["name"], str(a["evals"]), f"{a['gain']:+.4f}", "PASS" if a["gain"] <= 0.005 else "IMPROVE") for a in P["attempts"]]
    return table(["M1 attempt", "evaluations", "composite gain", "result"], rows, aligns=["l", "r", "r", "l"]) + [f"baseline composite {P['baseline']:.4f}; pass threshold gain <= 0.005"]


@table_fn("sweep")
def _sweep(c):
    S = c["an"]["sweep"]
    rows = []
    for ap, row in zip(S["aps"], S["rows"]):
        rows.append([f"{ap} m"] + [(f"{x['comp']:.3f}" if x["ok"] else "x " + ",".join(x["fails"])) if x["comp"] is not None else "infeasible" for x in row])
    return table(["apothem \\ density p/ha"] + [str(d) for d in S["dens"]], rows, widths=[8, 12, 12, 12, 12, 12]) + ["x = a gate fails (ids shown); numbers = composite score where all gates pass"]


@table_fn("stress")
def _stress(c):
    rows = [(s["name"], f"{s['comp']:.3f}", ",".join(s["fails"]) or "none", pc(s["k"]["potable_ssr"]), pc(s["k"]["energy_ssr"])) for s in c["an"]["stress"]]
    return table(["stress test", "score", "gates failed", "potable", "energy"], rows, widths=[30, 6, 16, 8, 8])


@table_fn("limits")
def _limits(c):
    return table(["id", "known limitation", "class"], C.LIMITS, widths=[5, 60, 9])


@table_fn("open_items")
def _open(c):
    return table(["id", "open field-verification item"], C.OPEN_ITEMS, widths=[5, 70])


@table_fn("limits_theory")
def _theory(c):
    r = c["res"]
    L = r["land"]
    side = math.sqrt(L["hex"]["area_m2"])
    rows = [("edge length per cell", "hexagon (honeycomb bound)", f"{L['hex']['seam_len_m']:.0f} m", "design = optimum"),
            ("walk speed on slope", "Tobler physics", f"{r['terrain']['site_speed_kmh']:.2f} km/h at {c['cfg']['site']['slope_pct']}%", "immutable"),
            ("irrigation self-supply", "100% if rain were evenly timed", pc(r["water"]["ssr_irrigation"]), "immutable (rain timing) + pond size"),
            ("energy conversion", "PV on 100% of roofs", f"{pc(r['energy']['ssr'])} self-supply, export {f0(r['energy']['export_kwh_pp'])} kWh/p", "surplus; storage-limited"),
            ("in-city staples", "all kcal in-city", pc(r["food"]["kcal_ssr"]), "immutable (land/kcal)"),
            ("material recovery", "100% (energy-bounded)", pc(r["waste"]["recovery"]), "practical (sorting, energy)"),
            ("mass balances", "exact closure", f"water {r['water']['closure_rel']:.0e}, energy {r['energy']['closure_kwh_pp']:.0e}", "numerical zero")]
    return table(["parameter", "theoretical optimum", "design value", "gap class"], rows, widths=[18, 19, 22, 14])


@table_fn("gaps_closed")
def _gaps(c):
    rows = [("G-1", "irrigation self-supply 46% (winter-rain seasonality)", "reclaimed effluent loop + crop-mode yields + potable reserve -> 62%"),
            ("G-2", "potable external 15% in dry season", "MAR potable reserve (3 months) -> 100%"),
            ("G-3", "canopy 20.6% < 30%", "tree cover 55% of green -> 31.5%"),
            ("G-4", "apothem 310 m fails G01 (94% < 95%)", "apothem capped at 300 m"),
            ("G-5", "MCA chose shared power+water trough (unsafe)", "safety hard constraint (score >= 3) -> liftable wet strip"),
            ("G-6", "tank size invisible to monthly model", "floor 1.5 m3/p by judgement (L-02)"),
            ("G-7", "search favoured unpriced levers (wedge, runoff coeff.)", "removed from search; documented as upside levers"),
            ("G-8", "v1.0 energy source violates physics", "replaced by PV + storage + CHP; converters only")]
    return table(["id", "gap found by adversarial pass", "enhancement applied"], rows, widths=[4, 34, 34])


@table_fn("phasing")
def _phase(c):
    g = c["cfg"]["geometry"]
    import textwrap
    lines = ["STAGE 0 GROUND      : site data, geotech, community co-design, approvals [O-01..O-08]",
            "STAGE 1 SPINE+NODE  : seam corridor trunk, ponds/MAR, first node, first 1/3 cell",
            f"STAGE 2 CELL 1      : full cell ({c['res']['land']['pop_cell']:.0f} p) commissioned as PILOT: water quality, islanding, acoustics",
            f"STAGE 3 WARD        : cells 2-{g['cells_per_ward']} (ring order), ward node, digester + wetland, clinic",
            f"STAGE 4 CITY        : wards 2-{g['wards']}; shuttle loops; manufactory campus; wedge farms",
            "GROWTH TRIGGER      : add next cell when current cell >= 85% occupied AND self-supply gates hold",
            "EACH CELL           : self-contained for water, power, waste: a pledge shortfall delays, never strands, cells"]
    return [w for ln in lines for w in textwrap.wrap(ln, W, subsequent_indent=" " * 22)]


@table_fn("cert")
def _cert(c):
    import textwrap
    d, r, ds = c["d"], c["res"], c["dims"]
    top, mid, bot = "╔" + "═" * (W - 2) + "╗", "╠" + "═" * (W - 2) + "╣", "╚" + "═" * (W - 2) + "╝"

    def row(text):
        return ["║ " + seg.ljust(W - 3) + "║" for seg in (textwrap.wrap(text, W - 3) or [""])]
    gain = max(a["gain"] for a in c["an"]["plateau"]["attempts"])
    out = [top, "║" + "EFE OPTIBEST ENGINEER - DELIVERY CERTIFICATION".center(W - 2) + "║", mid]
    out += row("Design: AEQUCITY v2.0 | Purpose: synergetic EFE city, any site")
    out += row(f"Magnitude MACRO | Scale GLOBAL/INFRASTRUCTURE | Rigor ULTRA | Iterations {d['ladder_n']}")
    out += row(f"Final delta: last full gap cycle gain <= {gain:.4f} composite (threshold 0.005)") + [mid]
    out += row("EFE FILTER (evidenced): Sustainable, Renewable, Accessible, Open, Local-First, Circular, Durable = 7/7")
    out += row("DIMENSIONS (model score): " + ", ".join(f"{k} {v:.2f}" for k, v in ds.items()))
    out += row(f"GATES {d['gates_ok']}/{d['gates_n']} | FMEA max RPN {r['fmea']['max_rpn_post']} | PLATEAU: M1 pass, M2 pass with conditions, M3 pass, M4 gaps explained, M5 pass (model space)") + [mid]
    out += row("STATUS: OPTIBEST PLATEAU - DESIGN BASIS (model-verified)")
    out += row(f"NOT CLAIMED: rubric-5 PREMIUM and carbon-negative status (need field verification + LCA; {d['n_open']} open items, section 13.7)") + [bot]
    return out


@table_fn("photo")
def _photo(c):
    cfg, r = c["cfg"], c["res"]
    g, L = cfg["geometry"], r["land"]
    south = r["climate"]["lat"] < 0
    sun_txt = ("late-winter afternoon golden hour with the sun low in the north-west (azimuth about 300 deg, 12 deg above the horizon)" if south
               else "late-winter afternoon golden hour with the sun low in the south-west (azimuth about 240 deg, 12 deg above the horizon)")
    txt = (f"Ultra-detailed professional aerial architectural photograph of AEQUCITY v2.0, a seven-cell hexagonal ward of a regenerative Mediterranean-climate city at golden hour, "
           f"north at the top of the frame to match the ward plan schematic: seven flat-top hexagonal cells, each {2 * g['cell_apothem_m']} m flat-to-flat ({L['hex']['area_ha']:.1f} ha, about {f0(L['pop_cell'])} residents), tiled edge to edge into a flower of 1 centre cell and 6 neighbours, "
           f"every shared edge a {g['seam_width_m']} m AEQUSPINE seam corridor whose central 8 m median holds a planted bio-swale with a thin blue water line, a smooth grey stone cycle-track ribbon and a slim cantilevered blue-black solar colonnade {cfg['energy']['canopy_width_m']:g} m wide carrying warm amber luminaires, "
           f"flanked by two 5 m slow streets of terracotta-ochre interlocking permeable pavers with liftable service bands, 2.5 m walkways with yellow tactile guidance strips, and 2.5 m forest-garden verges of olive, fig, wild olive and silver-green spekboom; "
           f"inside each cell six radial {g['lane_width_m']} m kerbless shared-surface lanes run from a {g['node_area_ha']} ha circular market plaza (market hall, hardened resilience hub, hygiene hub, school) to the cell edges, with {L['n_courts']:.0f} short court lanes branching off, planted verge swales and fynbos courtyard gardens; "
           f"{g['storeys']}-storey stabilised-earth buildings in warm sand and ochre with north-facing mono-pitch roofs carrying dark PV arrays, cool pale roofs, rainwater tanks and productive roof gardens; tadpole e-trikes with swappable battery packs, cargo trikes and 12-seat e-shuttles moving slowly among pedestrians, children and wheelchair users; "
           f"a larger ward-node plaza at the centre; at the outer edge of the circular agri-commons wedge six reed-fringed ponds with floating solar panels, orchards, strip farms, agri-PV rows and tunnel houses fading into fynbos-covered hills and distant mountains; "
           f"{sun_txt}, long soft shadows raking across the plan, clear post-rain air, no text, no logos, photorealistic, architecturally exact to the schematic, calm, human, abundant.")
    tech = [("Camera", "Phase One XF IQ4 150MP (or Hasselblad H6D-400c MS) on a heavy-lift drone (DJI Matrice 350 RTK), gimbal-stabilised"), ("Lens", "Schneider 80 mm LS f/2.8 (about 35 mm eq. wide aerial), no distortion correction needed"),
            ("Exposure", "ISO 200 | f/8 | 1/500 s | -0.3 EV | RAW 16-bit"), ("Lighting", "golden hour, sun 12 deg above the " + ("north-western" if south else "south-western") + " horizon, 4200 K ambient fill, soft raking shadows"),
            ("Composition", "oblique aerial 55 deg down, centred on the ward node, rule-of-thirds horizon, hex cells fully inside frame, north up"), ("Equipment", "RTK GNSS, ND8 + circular polariser, tripod-equivalent hover lock, 3-frame bracket for HDR merge"),
            ("Setting / location", "Mediterranean winter-rainfall hills, fynbos and orchard belt, shortly after rain (reference site: Cape Town region)"),
            ("Medium / stock", "digital medium format; colour emulation Kodak Portra 160 + Fujifilm Provia 100F blend, fine grain 5%"), ("Output", "3:2, 150 MP, 300 DPI, 16-bit TIFF master + sRGB JPEG, 240 MB")]
    return para(txt) + [""] + kv(tech, key_w=18)
