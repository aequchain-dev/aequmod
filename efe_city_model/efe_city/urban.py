"""efe_city.urban - geometry, land budget, access, streets, transport, facilities, terrain, sun, sound."""
from __future__ import annotations

import math
import random
from functools import lru_cache

from .core import SQ3, EfeError, gini, percentile, subsystem

_NORMALS = [(math.cos(math.radians(t)), math.sin(math.radians(t))) for t in (90, 30, 150)]


def hex_metrics(a):
    r = 2 * a / SQ3
    area = 2 * SQ3 * a * a
    return {"apothem_m": a, "circumradius_m": r, "area_m2": area, "area_ha": area / 1e4,
            "perimeter_m": 6 * r, "seam_len_m": 3 * r}


@lru_cache(maxsize=512)
def _sample_hex(a, n, seed):
    rng = random.Random(seed)
    r = 2 * a / SQ3
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(-r, r), rng.uniform(-a, a)
        if SQ3 * abs(x) + abs(y) <= SQ3 * r:
            pts.append((x, y))
    return tuple(pts)


def _stats(d, mpm, lim_m):
    n = len(d)
    mean = sum(d) / n
    return {"mean_m": mean, "p95_m": percentile(d, 95), "max_m": max(d), "mean_min": mean / mpm,
            "p95_min": percentile(d, 95) / mpm, "max_min": max(d) / mpm,
            "cov": sum(1 for v in d if v <= lim_m) / n, "gini": gini(d)}


def access_hex(a, detour, speed_kmh, n=4000, seed=7):
    """Walk-access of residents of a 7-cell ward: node (cell centre), nearest seam stop, ward node (centre cell)."""
    mpm = speed_kmh * 1000 / 60.0
    base = _sample_hex(float(a), int(n // 2), int(seed))
    d_node = [detour * math.hypot(x, y) for x, y in base]
    d_seam = [detour * (a - max(abs(x * c + y * s) for c, s in _NORMALS)) for x, y in base]
    d_ward = list(d_node)
    for k in range(6):
        th = math.radians(30 + 60 * k)
        cx, cy = 2 * a * math.cos(th), 2 * a * math.sin(th)
        d_ward += [detour * math.hypot(x + cx, y + cy) for x, y in base]
    return {"cell_node": _stats(d_node, mpm, 400.0), "seam_stop": _stats(d_seam, mpm, 400.0),
            "ward_node": _stats(d_ward, mpm, 15 * mpm)}


def access_concentric(leg, detour, speed_kmh, n=4000, seed=7):
    """Legacy concentric-radial layout: neighbourhood nodes, district nodes, radial transit spokes."""
    rng = random.Random(seed)
    mpm = speed_kmh * 1000 / 60.0
    rb1, rb2, rc2 = leg["ring_b_inner_m"], leg["ring_b_outer_m"], leg["ring_c_outer_m"]
    wb = leg["density_ratio_b_to_c"] * (rb2 ** 2 - rb1 ** 2)
    wc = rc2 ** 2 - rb2 ** 2
    th0 = 2 * math.pi / leg["spokes"]
    d_nb, d_ds, d_sp = [], [], []
    for _ in range(n):
        lo, hi = (rb1, rb2) if rng.random() < wb / (wb + wc) else (rb2, rc2)
        r = math.sqrt(rng.uniform(lo * lo, hi * hi))
        th = rng.uniform(0, 2 * math.pi)
        dth = abs((th % th0) - th0 / 2)           # distance from the mid-line between spokes
        dth = th0 / 2 - dth                       # angular distance to nearest spoke
        d_sp.append(detour * r * math.sin(min(dth, math.pi / 2)))
        d_nb.append(detour * leg["neighbourhood_radius_m"] * math.sqrt(rng.random()))
        d_ds.append(detour * leg["district_radius_m"] * math.sqrt(rng.random()))
    return {"cell_node": _stats(d_nb, mpm, 400.0), "seam_stop": _stats(d_sp, mpm, 400.0),
            "ward_node": _stats(d_ds, mpm, 15 * mpm)}


@subsystem("access")
def access(cfg, res):
    g = cfg["geometry"]
    if g["layout"] == "hex_cellular":
        out = access_hex(g["cell_apothem_m"], g["detour_factor"], g["walk_speed_kmh"], g["mc_samples"], g["seed"])
    elif g["layout"] == "concentric_radial":
        out = access_concentric(cfg["legacy"], g["detour_factor"], g["walk_speed_kmh"], g["mc_samples"], g["seed"])
    else:
        raise EfeError(f"unknown layout '{g['layout']}'")
    out["layout"] = g["layout"]
    return out


@subsystem("land")
def land(cfg, res):
    g, secs = cfg["geometry"], cfg["sections"]
    a = float(g["cell_apothem_m"])
    hm = hex_metrics(a)
    pop = g["gross_density_p_ha"] * hm["area_ha"]
    foot = pop * g["gfa_per_capita_m2"] / g["storeys"]
    n_courts = pop / g["court_persons"]
    lengths = {"seam": hm["seam_len_m"], "lane": 6 * a + n_courts * g["court_lane_m"],
               "path": g["path_m_per_ha"] * hm["area_ha"]}
    widths = {"seam": g["seam_width_m"], "lane": g["lane_width_m"], "path": g["path_width_m"]}
    by_class, verge, corridor = {}, 0.0, {}
    for k, sec in secs.items():
        tot = sum(w for _, w, _ in sec)
        if abs(tot - widths[k]) > 1e-6:
            raise EfeError(f"section '{k}' widths sum to {tot} m, expected {widths[k]} m")
        corridor[k] = tot * lengths[k]
        for name, w, cls in sec:
            by_class[cls] = by_class.get(cls, 0.0) + w * lengths[k]
            if "verge" in name:
                verge += w * lengths[k]
    node = g["node_area_ha"] * 1e4
    rest = hm["area_m2"] - foot - sum(corridor.values()) - node
    if rest <= 0:
        raise EfeError("infeasible: no plot area left; lower density or corridor widths")
    surf = dict(by_class)
    surf["roof"] = foot

    def add(c, v):
        surf[c] = surf.get(c, 0.0) + v
    add("permeable_walk", node * g["plaza_hard_fraction"])
    add("green", node * (1 - g["plaza_hard_fraction"]))
    add("permeable_walk", rest * g["plot_hard_fraction"])
    add("green", rest * (1 - g["plot_hard_fraction"]))
    prod = rest * (1 - g["plot_hard_fraction"]) * g["plot_productive_fraction"] + verge * g["edible_verge_fraction"]
    cells = g["wards"] * g["cells_per_ward"]
    built = cells * hm["area_m2"]
    total = built / (1 - g["wedge_fraction"] - g["nature_fraction"])
    city = {"cells": cells, "pop": cells * pop, "built_m2": built, "total_m2": total,
            "wedge_area_m2": total * g["wedge_fraction"], "nature_area_m2": total * g["nature_fraction"],
            "radius_km": math.sqrt(total / math.pi) / 1000.0, "gross_density_p_ha": cells * pop / (total / 1e4)}
    shares = {"buildings": foot, "seams": corridor["seam"], "lanes": corridor["lane"], "paths": corridor["path"],
              "node": node, "plots": rest}
    return {"hex": hm, "pop_cell": pop, "footprint_m2": foot, "n_courts": n_courts, "lengths_m": lengths,
            "corridor_m2": corridor, "surface_m2": surf, "verge_m2": verge, "prod_cell_m2": prod, "plots_m2": rest,
            "node_m2": node, "shares_pct": {k: 100 * v / hm["area_m2"] for k, v in shares.items()}, "city": city}


def ssd_m(v_kmh, t_react, decel, grade=0.0):
    """Stopping sight distance (m); grade as fraction, positive uphill."""
    v = v_kmh / 3.6
    return v * t_react + v * v / (2 * (decel + 9.81 * grade))


@subsystem("streets", needs=("land",))
def streets(cfg, res):
    s, g, L = cfg["streets"], cfg["geometry"], res["land"]
    rows = []
    for cls in ("seam", "lane", "path"):
        v = s["speed_kmh"][cls]
        drive = [w for _, w, c in cfg["sections"][cls] if c == "permeable_street"]
        clear = (max(drive) - 2 * s["clearance_m"]) if drive else 0.0
        rows.append({"class": cls, "speed_kmh": v, "ssd_flat_m": ssd_m(v, s["react_s"], s["decel_ms2"]),
                     "ssd_down8_m": ssd_m(v, s["react_s"], s["decel_ms2"], -0.08),
                     "clear_m": clear, "emergency_ok": clear >= s["emergency_clear_m"],
                     "width_m": sum(w for _, w, _ in cfg["sections"][cls])})
    ha = L["hex"]["area_ha"]
    junctions = 2 + 3 + L["n_courts"]
    hex_cp = junctions * s["leg3"] / ha
    grid_cp = (1e4 / s["grid_block_m"] ** 2) * s["leg4"]
    drv_len = L["lengths_m"]["seam"] + L["lengths_m"]["lane"]
    layout = g["layout"]
    return {"rows": rows, "conflict_pts_ha_hex": hex_cp, "conflict_pts_ha_grid": grid_cp,
            "conflict_pts_ha": hex_cp if layout == "hex_cellular" else grid_cp,
            "max_reach_m": 0.5 * 1e4 / (drv_len / ha), "hose_reach_m": s["hose_reach_m"],
            "reach_ok": 0.5 * 1e4 / (drv_len / ha) <= s["hose_reach_m"]}


@subsystem("transport", needs=("land", "access"))
def transport(cfg, res):
    t, L = cfg["transport"], res["land"]
    pop = L["city"]["pop"]
    sh = t["modal_share"]
    peak_trips = pop * t["trips_pp_day"] * sh["shuttle"] * t["peak_hour_fraction"]
    pax_km_h = peak_trips * t["avg_trip_km"]["shuttle"]
    cap = t["shuttle_seats"] * t["load_factor"] * t["shuttle_speed_kmh"]
    fleet = math.ceil(pax_km_h / cap * (1 + t["spare_fraction"]))
    pax_km_yr = pop * t["trips_pp_day"] * 365 * sh["shuttle"] * t["avg_trip_km"]["shuttle"]
    shuttle_kwh = pax_km_yr / (t["shuttle_seats"] * t["load_factor"]) * t["shuttle_kwh_km"]
    trike_km = pop * t["trips_pp_day"] * 365 * sh["cycle_trike"] * t["avg_trip_km"]["cycle_trike"] / t["trike_occupancy"]
    trike_kwh = trike_km * t["trike_kwh_km"]
    seam_total_km = L["lengths_m"]["seam"] * L["city"]["cells"] / 1000.0
    return {"fleet_shuttles": fleet, "fleet_per_1000": 1000 * fleet / pop, "peak_trips_h": peak_trips,
            "shuttle_kwh_pp": shuttle_kwh / pop, "trike_kwh_pp": trike_kwh / pop,
            "energy_kwh_pp": (shuttle_kwh + trike_kwh) / pop, "seam_route_km": seam_total_km,
            "stop_dist_p95_m": res["access"]["seam_stop"]["p95_m"], "stop_cov400": res["access"]["seam_stop"]["cov"]}


@subsystem("facilities", needs=("land",))
def facilities(cfg, res):
    f, L, g = cfg["facilities"], res["land"], cfg["geometry"]
    cells, wards, P = L["city"]["cells"], g["wards"], L["pop_cell"]
    courts = L["n_courts"] * cells
    peak = f["hub_peak_fraction"] * P
    wc = math.ceil(peak / f["persons_per_wc"])
    hub = {"peak_users": peak, "wc": wc, "accessible_wc": max(2, math.ceil(0.15 * wc)),
           "basins": math.ceil(1.3 * wc), "showers": math.ceil(peak / f["persons_per_shower"]),
           "washers": math.ceil(P / f["persons_per_washer"]),
           "water_m3_day": P * f["hub_use_fraction"] * f["lpd_hub"] / 1000.0}
    water_pts = (L["lengths_m"]["seam"] / f["water_point_spacing_m"] + 2 + L["n_courts"]) * cells
    rows = [(n, q * cells) for n, q in f["per_cell"]] + [(n, q * wards) for n, q in f["per_ward"]] + \
           [(n, q) for n, q in f["per_city"]] + [(n + " (per court)", courts) for n in f["per_court"]]
    return {"courts": courts, "hub": hub, "drinking_points": water_pts, "rows": rows}


def tobler_kmh(slope):
    """Tobler hiking function; slope = rise/run (uphill positive)."""
    return 6.0 * math.exp(-3.5 * abs(slope + 0.05))


@subsystem("terrain")
def terrain(cfg, res):
    g, site = cfg["geometry"], cfg["site"]
    v0 = 2.0 / (1 / tobler_kmh(0.0) + 1 / tobler_kmh(-0.0))
    table = []
    for pct in (0, 2, 5, 8, 10, 15, 20):
        s = pct / 100.0
        v = 2.0 / (1 / tobler_kmh(s) + 1 / tobler_kmh(-s))
        table.append({"slope_pct": pct, "speed_kmh": v, "rel": v / v0, "apothem_eff_m": g["cell_apothem_m"] * v / v0})
    s = site["slope_pct"] / 100.0
    v = 2.0 / (1 / tobler_kmh(s) + 1 / tobler_kmh(-s))
    return {"table": table, "site_speed_kmh": v, "site_rel": v / v0,
            "p95_min_at_site": res["access"]["cell_node"]["p95_min"] * v0 / v if "access" in res else None}


@subsystem("sungeo", needs=("climate",))
def sungeo(cfg, res):
    lat, g = res["climate"]["lat"], cfg["geometry"]
    dec = 23.44
    winter = 90 - abs(lat - (dec if lat < 0 else -dec))
    summer = 90 - abs(lat - (-dec if lat < 0 else dec))
    gap = g["lane_width_m"] + 2 * g["setback_m"]
    rows = []
    for st in (2, 3, 4, 5):
        h = st * g["floor_height_m"] + 0.5
        req = (h - 1.0) / math.tan(math.radians(winter))
        rows.append({"storeys": st, "height_m": h, "spacing_req_m": req, "spacing_actual_m": gap, "ok": gap >= req})
    return {"lat": lat, "winter_noon_elev": winter, "summer_noon_elev": summer, "rows": rows,
            "max_storeys_on_lane": max([r["storeys"] for r in rows if r["ok"]] or [1])}


@subsystem("acoustics", needs=("land",))
def acoustics(cfg, res):
    a = cfg["acoustics"]
    out = {}
    for cls, vt in (("seam", "shuttle"), ("lane", "trike")):
        n, lmax = a["veh_per_h"][cls], a["lmax_7_5m"][vt]
        leq7 = lmax + 10 * math.log10(max(n, 1) * a["pass_s"] / 3600.0)
        d = a["facade_dist_m"][cls]
        leq = leq7 - a["ground_db_per_doubling"] * math.log2(d / 7.5)
        out[cls] = {"veh_per_h": n, "leq_7_5m": leq7, "facade_m": d, "leq_facade": leq}
    out["who_lden_db"], out["who_lnight_db"] = 53, 45
    return out
