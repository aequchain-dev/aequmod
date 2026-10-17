"""efe_city.analysis - evidence runs used by the blueprint: ladder, plateau search, sweeps, stress tests, site adapter."""
from __future__ import annotations

import copy
import json
import time

from .core import apply_overrides, load_json, DATA, EfeError
from . import evaluate as ev


def sweep_density_apothem(cfg, dens=(70, 80, 90, 100, 110), aps=(260, 280, 300, 320, 340)):
    rows = []
    for a in aps:
        row = []
        for d in dens:
            c = apply_overrides(cfg, [f"geometry.gross_density_p_ha={d}", f"geometry.cell_apothem_m={a}"])
            try:
                x = ev.evaluate(c)
                row.append({"comp": x["composite"], "ok": all(g["ok"] for g in x["gates"]),
                            "fails": [g["id"] for g in x["gates"] if not g["ok"]]})
            except EfeError:
                row.append({"comp": None, "ok": False, "fails": ["infeasible"]})
        rows.append(row)
    return {"dens": list(dens), "aps": list(aps), "rows": rows}


STRESS = [("rain -20%", ["site.rain_factor=0.8"]), ("solar -10%", ["site.ghi_factor=0.9"]),
          ("energy demand +20%", ["energy.demand_factor=1.2"]), ("potable use +30% (72 L/p/d)", ["water.potable_lpd=72"]),
          ("density +20% (108 p/ha)", ["geometry.gross_density_p_ha=108"]), ("density -20% (72 p/ha)", ["geometry.gross_density_p_ha=72"]),
          ("cloud variability +50%", ["energy.cloud_sigma=0.52"]), ("storage -33% (6.3 kWh/p)", ["energy.storage_kwh_pp=6.3"]),
          ("slope 8% (walk speed penalty)", ["site.slope_pct=8"]),
          ("hazard: cyclone coast", ['site.hazard_profile="stress_cyclone"']),
          ("hazard: tornado plains", ['site.hazard_profile="stress_tornado"']),
          ("hazard: high seismicity", ['site.hazard_profile="stress_seismic"'])]


def stress_tests(cfg):
    out = []
    for name, ov in STRESS:
        x = ev.evaluate(apply_overrides(cfg, ov))
        out.append({"name": name, "comp": x["composite"], "fails": [g["id"] for g in x["gates"] if not g["ok"]],
                    "k": {n: x["k"][n] for n in ("potable_ssr", "irrigation_ssr", "energy_ssr", "fresh_ssr", "flood_catch_ha", "lold")}})
    return out


def site_adapter(cfg):
    """Global compatibility: swap climate + hazard profile, report gates, then auto-tune levers per site."""
    pairs = [("cape_town", "cape_town"), ("johannesburg", "johannesburg"), ("durban", "durban"),
             ("lisbon", "lisbon"), ("nairobi", "nairobi")]
    out = []
    for cl, hz in pairs:
        c = apply_overrides(cfg, [f'site.climate="{cl}"', f'site.hazard_profile="{hz}"'])
        x = ev.evaluate(c)
        fails0 = [g["id"] for g in x["gates"] if not g["ok"]]
        best, vec, n = ev.coordinate_search(c, passes=2)
        c2 = ev._set(c, vec)
        y = ev.evaluate(c2)
        out.append({"site": cl, "label": load_json(DATA / "climates.json")[cl]["label"], "comp0": x["composite"], "fails0": fails0,
                    "comp1": y["composite"], "fails1": [g["id"] for g in y["gates"] if not g["ok"]],
                    "tuned": {k.split(".")[-1]: round(v, 2) for k, v in vec.items()},
                    "k": {n_: y["k"][n_] for n_ in ("potable_ssr", "irrigation_ssr", "energy_ssr", "fresh_ssr")},
                    "opt_tilt": y["res"]["solar"]["opt_tilt"], "lat": y["res"]["climate"]["lat"]})
    return out


def run_analysis(cfg, quick=False):
    t0 = time.time()
    base = ev.evaluate(cfg)
    out = {"ladder": ev.iterations(cfg), "plateau": ev.plateau_report(cfg, 60 if quick else 160, 60 if quick else 160),
           "sweep": sweep_density_apothem(cfg), "stress": stress_tests(cfg), "adapter": [] if quick else site_adapter(cfg)}
    out["baseline"] = {"composite": base["composite"], "dims": base["dims"], "k": base["k"],
                       "gates": base["gates"], "scores": base["s"]}
    out["seconds"] = time.time() - t0
    return out
