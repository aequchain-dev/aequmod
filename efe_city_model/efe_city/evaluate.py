"""efe_city.evaluate - KPIs, OPTIBEST dimension scoring, hard gates, design iterations and plateau search."""
from __future__ import annotations

import copy
import json
import random

from .core import PKG, EfeError, apply_overrides, deep_update, get, load_json, run_all, set_path

# key: (worst, best, weight, dimension, label, unit)   -- score = clip((v-worst)/(best-worst), 0, 1)
SPEC = {
    "access_cov400": (0.10, 0.95, 4, "functional", "residents within 400 m of a daily-needs node", "share"),
    "ward_p95_min": (45.0, 15.0, 3, "functional", "P95 walk time to ward-level services", "min"),
    "potable_ssr": (0.0, 1.0, 4, "functional", "potable water self-supply", "share"),
    "irrigation_ssr": (0.0, 1.0, 2, "functional", "irrigation water self-supply", "share"),
    "energy_ssr": (0.0, 1.0, 4, "functional", "electricity self-supply (annual, daily-resolved)", "share"),
    "fresh_ssr": (0.0, 1.0, 3, "functional", "fresh produce self-supply (in-city + ward belt)", "share"),
    "corridor_m_pp": (4.0, 2.3, 2, "efficiency", "street + utility corridor length per capita", "m/p"),
    "excavation_m3_pp": (30.0, 5.0, 2, "efficiency", "excavation per capita (trenches + tunnels)", "m3/p"),
    "capex_pp": (80000.0, 35000.0, 3, "efficiency", "capex per capita (planning-grade)", "USD/p"),
    "external_cost_pp": (3000.0, 600.0, 3, "efficiency", "external cost per member per year", "USD/p/yr"),
    "recovery": (0.60, 0.97, 2, "efficiency", "material recovery rate", "share"),
    "runoff_c": (0.90, 0.15, 2, "robustness", "peak runoff coefficient (area-weighted, attenuated)", "-"),
    "flood_catch_ha": (1.0, 60.0, 2, "robustness", "max catchment per overland route (1:100, DV<=0.4)", "ha"),
    "shelter_min": (45.0, 6.0, 3, "robustness", "P95 walk time to hardened shelter", "min"),
    "shelter_cap": (0.0, 1.2, 2, "robustness", "hardened shelter capacity ratio", "-"),
    "conflict_pts_ha": (40.0, 8.0, 2, "robustness", "vehicle conflict points per hectare", "n/ha"),
    "lold": (60.0, 0.0, 2, "robustness", "days per year with energy import (loss-of-load days)", "d"),
    "canopy_cover": (0.0, 0.30, 1, "robustness", "tree + PV canopy cover of cell", "share"),
    "growth_step_pop": (25000.0, 2800.0, 2, "scalability", "population added per growth step", "p"),
    "complexity": (15.0, 5.0, 3, "maintainability", "distinct trench + section + tunnel systems", "n"),
    "inspectable": (0.0, 0.8, 2, "maintainability", "utility length inspectable without breaking surface", "share"),
    "synergy_pairs": (100.0, 130.0, 2, "innovation", "subsystem pairs with shared space or flow", "n"),
    "elegance": (0.01, 0.20, 3, "elegance", "purpose achievement / complexity", "-"),
}
DIMS = ["functional", "efficiency", "robustness", "scalability", "maintainability", "innovation", "elegance"]


def kpis(cfg, res):
    A, Y = res["access"], res["synergy"]
    k = {"access_cov400": A["cell_node"]["cov"], "ward_p95_min": A["ward_node"]["p95_min"],
         "potable_ssr": res["water"]["ssr_potable"], "irrigation_ssr": res["water"]["ssr_irrigation"],
         "energy_ssr": res["energy"]["ssr"], "fresh_ssr": res["food"]["fresh_ssr"],
         "corridor_m_pp": Y["corridor_m_pp"], "excavation_m3_pp": Y["excavation_m3_pp"],
         "capex_pp": res["economics"]["capex_pp"], "external_cost_pp": res["economics"]["external_cost_pp"],
         "recovery": res["waste"]["recovery"], "runoff_c": res["flood"]["c_peak"],
         "flood_catch_ha": res["flood"]["max_catchment_ha"], "shelter_min": res["shelter"]["walk_min"],
         "shelter_cap": res["shelter"]["capacity_ratio"], "conflict_pts_ha": res["streets"]["conflict_pts_ha"],
         "lold": float(res["energy"]["lold_days"]), "canopy_cover": res["thermal"]["canopy_cover"],
         "growth_step_pop": Y["growth_step_pop"], "complexity": float(Y["complexity"]),
         "inspectable": Y["inspectable_fraction"], "synergy_pairs": float(Y["synergy_pairs"])}
    return k


def _clip01(x):
    return max(0.0, min(1.0, x))


def scores(k):
    s = {n: _clip01((k[n] - w) / (b - w)) for n, (w, b, *_rest) in SPEC.items() if n != "elegance"}
    func = [s[n] for n, v in SPEC.items() if v[3] == "functional"]
    purpose = sum(func) / len(func)
    k["elegance"] = purpose / k["complexity"]
    w, b = SPEC["elegance"][0], SPEC["elegance"][1]
    s["elegance"] = _clip01((k["elegance"] - w) / (b - w))
    return s


def composite(s):
    num = sum(SPEC[n][2] * v for n, v in s.items())
    return num / sum(SPEC[n][2] for n in s)


def dimension_scores(s):
    out = {}
    for d in DIMS:
        ks = [n for n, v in SPEC.items() if v[3] == d]
        out[d] = sum(SPEC[n][2] * s[n] for n in ks) / sum(SPEC[n][2] for n in ks)
    return out


def rubric(score):
    """Model-space rubric. Level 5 (PREMIUM) is reserved for plateau-verified AND field-verified evidence."""
    return 1 if score < 0.2 else 2 if score < 0.5 else 3 if score < 0.8 else 4


def gates(cfg, res, k):
    st = res["streets"]["rows"]
    drv = [r for r in st if r["class"] != "path"]
    sg = res["sungeo"]
    g = [("G01", "walk access: >=95% of residents within 400 m of a daily node", k["access_cov400"] >= 0.95, k["access_cov400"]),
         ("G02", "ward services within 15 min walk (P95)", k["ward_p95_min"] <= 15.0, k["ward_p95_min"]),
         ("G03", "potable self-supply >= 95%", k["potable_ssr"] >= 0.95, k["potable_ssr"]),
         ("G04", "electricity self-supply >= 95%", k["energy_ssr"] >= 0.95, k["energy_ssr"]),
         ("G05", "fresh produce self-supply >= 95%", k["fresh_ssr"] >= 0.95, k["fresh_ssr"]),
         ("G06", "material recovery >= 95%", k["recovery"] >= 0.95, k["recovery"]),
         ("G07", "hardened shelter <= 6 min walk, capacity >= 1.0", k["shelter_min"] <= 6.0 and k["shelter_cap"] >= 1.0, k["shelter_min"]),
         ("G08", "1:100 overland route catchment >= 20 ha at DV <= 0.4", k["flood_catch_ha"] >= 20.0, k["flood_catch_ha"]),
         ("G09", "vehicle conflict points <= 12 per ha", k["conflict_pts_ha"] <= 12.0, k["conflict_pts_ha"]),
         ("G10", "canopy cover >= 30%", k["canopy_cover"] >= 0.30, k["canopy_cover"]),
         ("G11", "emergency clear width >= 3.7 m on all drivable classes", all(r["emergency_ok"] for r in drv), min(r["clear_m"] for r in drv)),
         ("G12", "hose reach <= 45 m from a drivable street", res["streets"]["reach_ok"], res["streets"]["max_reach_m"]),
         ("G13", "FMEA closed: post-mitigation RPN <= 100, all S>=9 mitigated", res["fmea"]["gate"], res["fmea"]["max_rpn_post"]),
         ("G14", "water mass balance closes (|rel| < 1e-9)", abs(res["water"]["closure_rel"]) < 1e-9, res["water"]["closure_rel"]),
         ("G15", "energy balance closes (|kWh/p| < 1e-6)", abs(res["energy"]["closure_kwh_pp"]) < 1e-6, res["energy"]["closure_kwh_pp"]),
         ("G16", ">=3 storeys admissible on lanes (winter solar access)", sg["max_storeys_on_lane"] >= 3, sg["max_storeys_on_lane"]),
         ("G17", "seam facade noise <= WHO L_den 53 dB (indicative)", res["acoustics"]["seam"]["leq_facade"] <= 53, res["acoustics"]["seam"]["leq_facade"]),
         ("G18", "drought (design profile): unmet potable <= 5% under restrictions", res["water"]["drought"]["unmet_pot_pct"] <= 5.0, res["water"]["drought"]["unmet_pot_pct"])]
    return [{"id": i, "text": t, "ok": bool(ok), "value": v} for i, t, ok, v in g]


def evaluate(cfg):
    res = run_all(cfg)
    k = kpis(cfg, res)
    s = scores(k)
    return {"res": res, "k": k, "s": s, "composite": composite(s), "dims": dimension_scores(s), "gates": gates(cfg, res, k)}


def iterations(base_cfg, path=None):
    its = load_json(path or PKG / "configs" / "iterations.json")
    cfg, out, prev = copy.deepcopy(base_cfg), [], None
    for it in its:
        cfg = deep_update(cfg, it["over"]) if it["id"] != "I8" else cfg
        ev = evaluate(cfg)
        out.append({"id": it["id"], "name": it["name"], "k": ev["k"], "s": ev["s"], "composite": ev["composite"],
                    "dims": ev["dims"], "gates_ok": sum(g["ok"] for g in ev["gates"]), "gates_n": len(ev["gates"]),
                    "delta": None if prev is None else ev["composite"] - prev})
        prev = ev["composite"]
    return out


# ------------------------------------------------------------------ plateau search (model space)
SPACE = {"geometry.gross_density_p_ha": (60.0, 140.0), "geometry.cell_apothem_m": (240.0, 380.0),
         "water.tank_m3_pp": (1.0, 4.0), "water.pond_m3_pp": (0.5, 8.0),
         "energy.storage_kwh_pp": (2.0, 14.0), "energy.canopy_width_m": (0.0, 8.0), "energy.roof_usable": (0.3, 0.7),
         "energy.agri_pv_fraction": (0.0, 0.15), "geometry.plot_productive_fraction": (0.3, 0.7),
         "thermal.tree_cover_green": (0.3, 0.7)}
# NOTE: unpriced levers (geometry.wedge_fraction, water.wedge_runoff_coeff) are deliberately NOT searched:
# the cost model has no land value or earthworks cost, so the optimiser would exploit them. They are policy / upside levers.


def objective(cfg):
    try:
        ev = evaluate(cfg)
    except EfeError:
        return -1.0, None
    ok = all(g["ok"] for g in ev["gates"])
    return ev["composite"] - (0.0 if ok else 0.25 + 0.01 * sum(not g["ok"] for g in ev["gates"])), ev


def _set(cfg, vec):
    c = copy.deepcopy(cfg)
    for k, v in vec.items():
        set_path(c, k, round(v, 4))
    return c


def coordinate_search(cfg, space=SPACE, passes=3):
    cur = {k: get(cfg, k) for k in space}
    best, _ = objective(cfg)
    n = 0
    for _ in range(passes):
        improved = False
        for k, (lo, hi) in space.items():
            for step in (0.10, 0.05, -0.05, -0.10):
                cand = dict(cur)
                cand[k] = min(hi, max(lo, cur[k] + step * (hi - lo)))
                val, _ = objective(_set(cfg, cand))
                n += 1
                if val > best + 1e-9:
                    best, cur, improved = val, cand, True
        if not improved:
            break
    return best, cur, n


def random_search(cfg, n=200, seed=1, space=SPACE, sigma=None):
    rng = random.Random(seed)
    base = {k: get(cfg, k) for k in space}
    best, bvec = objective(cfg)[0], dict(base)
    for _ in range(n):
        vec = {}
        for k, (lo, hi) in space.items():
            vec[k] = rng.uniform(lo, hi) if sigma is None else min(hi, max(lo, rng.gauss(base[k], sigma * (hi - lo))))
        val, _ = objective(_set(cfg, vec))
        if val > best:
            best, bvec = val, vec
    return best, bvec, n


def plateau_report(cfg, n_random=160, n_local=160):
    base, _ = objective(cfg)
    a1 = coordinate_search(cfg)
    a2 = random_search(cfg, n_random, seed=2)
    a3 = random_search(cfg, n_local, seed=3, sigma=0.06)
    a4 = random_search(cfg, n_local, seed=4, sigma=0.15)
    att = [("coordinate +-5/10% moves", a1), ("global random search", a2), ("local search sigma 6%", a3), ("local search sigma 15%", a4)]
    return {"baseline": base, "attempts": [{"name": n, "best": b, "gain": b - base, "evals": e, "vec": v} for n, (b, v, e) in att],
            "plateau": all(b - base <= 0.005 for _, (b, _, _) in att)}
