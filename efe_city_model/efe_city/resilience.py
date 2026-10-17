"""efe_city.resilience - multi-hazard structural doctrine, foundations, flood routes, shelters,
delivery-means MCA (above/below land, trough, gallery...) and FMEA. Planning-grade: local codes govern."""
from __future__ import annotations

import math
import random
from functools import lru_cache

from .core import DATA, EfeError, load_json, subsystem

RHO_AIR = 1.25
SOIL_S = {"A": 1.0, "B": 1.2, "C": 1.15, "D": 1.35, "E": 1.4}            # EC8 type-1 spectrum soil factor
EF_MAX_MS = {0: 38, 1: 49, 2: 60, 3: 74, 4: 89, 5: 100}                  # upper bound of EF class, 3-s gust
SYSTEMS = [  # ordered by preference (lowest embodied impact first); max_pga_g = planning threshold at <=3 storeys
    ("unreinforced_earth", "AEQUBLOCK earth walls, unreinforced", 1.5, 9.0, 0.05),
    ("confined_earth", "AEQUBLOCK earth walls + ring beams/ties/confinement", 2.0, 9.0, 0.15),
    ("timber_bamboo_frame", "timber/bamboo frame, light infill", 3.0, 3.5, 0.40),
    ("steel_timber_hybrid", "FRAME CONSTRUCTIO steel-timber hybrid, bolted", 4.0, 4.0, 0.60)]
FOUNDATIONS = {
    "A": ("rock / very dense", "strip or rubble-trench footing keyed into rock; no deep works"),
    "B": ("dense sand-gravel / very stiff clay", "strip footing + ground beam, or stone rubble-trench; toe drainage"),
    "C": ("medium-dense / stiff", "stiffened raft or ground-beam grid on geopolymer precast pads; screw piles as alternative"),
    "D": ("loose / soft", "screw piles (reusable, no spoil) + ring beam, or raft on engineered gravel mat"),
    "E": ("very soft / liquefiable", "driven/screw piles to firm stratum + ground improvement; light structures only")}


def wind_q_kpa(v):
    return 0.5 * RHO_AIR * v * v / 1000.0


def seismic_cs(ag, soil, q):
    """EC8-style plateau design spectrum ordinate Sd/g (planning value)."""
    return max(ag * SOIL_S[soil] * 2.5 / q, 0.2 * ag)


def street_flow(Q, z, n, slope):
    """Triangular street channel (side slopes z:1): depth, velocity, d*v for flow Q (m3/s), Manning."""
    lo, hi = 1e-4, 3.0
    for _ in range(70):
        d = (lo + hi) / 2
        a = z * d * d
        p = 2 * d * math.sqrt(1 + z * z)
        q = (a / n) * (a / p) ** (2.0 / 3.0) * math.sqrt(slope)
        lo, hi = (d, hi) if q < Q else (lo, d)
    d = (lo + hi) / 2
    v = Q / (z * d * d)
    return d, v, d * v


def profile_design(hz, soil):
    q = wind_q_kpa(hz["gust_ms"])
    ag = hz["pga_g"]
    sysname = next((s for s in SYSTEMS if s[4] >= ag), SYSTEMS[-1])
    shelter_v = 112.0 if hz["tornado_ef"] >= 3 else EF_MAX_MS.get(hz["tornado_ef"], 38)
    return {"q_kpa": q, "wall_kpa": 1.3 * q, "roof_uplift_kpa": max(0.0, 1.2 * q - 0.4), "edge_uplift_kpa": 2.0 * q - 0.4,
            "eave_tension_kn_m": max(0.0, 1.2 * q - 0.4) * 4.0, "shelter_v_ms": shelter_v,
            "shelter_q_kpa": wind_q_kpa(shelter_v), "safe_rooms": hz["tornado_ef"] >= 3,
            "cs": {s[0]: seismic_cs(ag, soil, s[2]) for s in SYSTEMS}, "system": sysname,
            "plinth_m": 0.5 + hz["surge_m"] + (0.3 if hz["flood100_24h_mm"] >= 200 else 0.0),
            "defensible_m": {"high": 30, "medium": 15, "low": 10}[hz["fire"]],
            "hurricane_envelope": hz["gust_ms"] >= 55, "max_storeys_outside_hubs": 2 if hz["gust_ms"] >= 55 else 3}


@subsystem("structure", needs=("hazard", "land"))
def structure(cfg, res):
    hz, L, r = res["hazard"], res["land"], cfg["resilience"]
    soil = cfg["site"]["soil_class"]
    cur = profile_design(hz, soil)
    haz = load_json(DATA / "hazards.json")
    table = {k: profile_design(v, soil) | {"label": v["label"], "hz": v} for k, v in haz.items() if not k.startswith("_")}
    canopy = L["hex"]["area_m2"] * res.get("thermal", {}).get("canopy_cover", 0.30)
    trees = canopy / r["crown_m2"]
    return {"current": cur, "profiles": table, "soil": soil, "foundation": FOUNDATIONS[soil],
            "trees_cell": trees, "trees_pp": trees / L["pop_cell"],
            "co2_t_cell_yr": (trees * 10 / 1000.0, trees * 25 / 1000.0), "windbreak_h_m": r["windbreak_height_m"]}


@subsystem("flood", needs=("land", "hazard"))
def flood(cfg, res):
    r, L, hz = cfg["resilience"], res["land"], res["hazard"]
    mode = cfg["water"]["drainage_mode"]
    S = L["surface_m2"]
    tot = sum(S.values())
    cm = r["c_peak"]

    def c_of(k):
        return cm["impervious"] if (mode == "piped" and k in ("permeable_walk", "permeable_street", "ribbon")) else cm[k]
    c_area = sum(S[k] * c_of(k) for k in S) / tot
    c_peak = c_area * (1 - (r["peak_attenuation_sponge"] if mode == "sponge" else 0.0))
    out = {}
    for tag, i in (("1in10", hz["i10_15_mm_h"]), ("1in100", hz["i100_15_mm_h"])):
        lo, hi = 0.0, 500.0
        for _ in range(60):
            a = (lo + hi) / 2
            d, v, dv = street_flow(c_peak * i * a / 360.0, r["street_z"], r["street_n"], r["street_slope"])
            lo, hi = (a, hi) if (dv <= 0.4 and d <= 0.3) else (lo, a)
        d1, v1, dv1 = street_flow(c_peak * i * 1.0 / 360.0, r["street_z"], r["street_n"], r["street_slope"])
        out[tag] = {"i_mm_h": i, "max_catchment_ha": lo, "d1_m": d1, "v1_ms": v1, "dv1": dv1,
                    "q1_m3s": c_peak * i / 360.0}
    return {"c_area": c_area, "c_peak": c_peak, "mode": mode, "events": out,
            "max_catchment_ha": out["1in100"]["max_catchment_ha"], "limits": {"dv": 0.4, "d_m": 0.3}}


@subsystem("shelter", needs=("land", "access"))
def shelter(cfg, res):
    r, L, A, g = cfg["resilience"], res["land"], res["access"], cfg["geometry"]
    if r["shelters"]:
        area = g["nonres_gfa_per_capita_m2"] * L["pop_cell"] * r["node_nonres_share"] * r["hardened_fraction"]
        return {"enabled": True, "area_m2": area, "capacity_ratio": area / (L["pop_cell"] * r["shelter_m2_pp"]),
                "walk_min": A["cell_node"]["p95_min"], "lead_time_ok": A["cell_node"]["p95_min"] <= 10.0}
    return {"enabled": False, "area_m2": 0.0, "capacity_ratio": 0.0, "walk_min": A["ward_node"]["p95_min"],
            "lead_time_ok": A["ward_node"]["p95_min"] <= 10.0}


# ----------------------------------------------------- delivery means: multi-criteria analysis
CRITERIA = ["capex", "wind", "flood", "fire", "seismic", "repair", "inspect", "adapt", "safety"]   # 5 = best
OPTIONS = {
    "power": {"overhead_bare": [5, 1, 5, 1, 3, 4, 5, 4, 1], "overhead_bundled": [4, 2, 5, 3, 3, 4, 4, 3, 3],
              "buried_direct": [3, 5, 3, 5, 3, 1, 1, 1, 4], "buried_ducted": [3, 5, 3, 5, 3, 3, 2, 3, 5],
              "accessible_trough": [3, 5, 4, 5, 4, 5, 5, 5, 4], "utility_gallery": [1, 5, 2, 3, 3, 5, 5, 5, 3],
              "in_structure": [3, 3, 5, 3, 3, 4, 4, 3, 3]},
    "water": {"buried_direct": [4, 5, 3, 5, 3, 2, 1, 2, 5], "liftable_wet_strip": [4, 5, 3, 5, 4, 4, 3, 3, 5],
              "shared_trough": [3, 5, 3, 5, 4, 5, 5, 4, 2], "utility_gallery": [1, 5, 2, 3, 3, 5, 5, 5, 3],
              "surface_temporary": [5, 3, 5, 3, 3, 5, 5, 5, 2]},
    "data": {"aerial": [5, 1, 5, 1, 3, 4, 5, 4, 3], "buried_microduct": [4, 5, 3, 5, 3, 2, 2, 2, 5],
             "accessible_trough": [4, 5, 4, 5, 4, 5, 5, 5, 5], "wireless_mesh": [4, 3, 5, 3, 5, 5, 5, 5, 4]}}


def hazard_weights(hz):
    w = dict.fromkeys(CRITERIA, 1.0)
    w["capex"], w["repair"], w["inspect"] = 1.5, 1.5, 1.5          # EFE: durable + repairable
    w["wind"] = 3.0 if hz["gust_ms"] >= 55 else 1.5 if hz["gust_ms"] >= 42 else 1.0
    w["flood"] = 3.0 if (hz["flood100_24h_mm"] >= 200 or hz["surge_m"] >= 1.0) else 1.5 if hz["flood100_24h_mm"] >= 120 else 1.0
    w["fire"] = {"high": 3.0, "medium": 1.5, "low": 1.0}[hz["fire"]]
    w["seismic"] = 3.0 if hz["pga_g"] >= 0.3 else 1.5 if hz["pga_g"] >= 0.1 else 1.0
    return w


SAFETY_MIN = 3        # hard constraint: options scoring < 3 on public safety are excluded (safety is never traded)


@lru_cache(maxsize=64)
def _mca(wkey, n=1000, seed=5):
    w = dict(zip(CRITERIA, wkey))
    out = {}
    rng = random.Random(seed)
    for util, all_opts in OPTIONS.items():
        opts = {o: v for o, v in all_opts.items() if v[CRITERIA.index("safety")] >= SAFETY_MIN}
        excluded = sorted(set(all_opts) - set(opts))
        base = {o: sum(w[c] * s for c, s in zip(CRITERIA, v)) / sum(w.values()) for o, v in opts.items()}
        best = max(base, key=base.get)
        wins = {o: 0 for o in opts}
        for _ in range(n):
            ww = {c: w[c] * rng.uniform(0.5, 1.5) for c in CRITERIA}
            tot = {}
            for o, v in opts.items():
                tot[o] = sum(ww[c] * min(5, max(1, s + rng.choice((-1, 0, 0, 1)))) for c, s in zip(CRITERIA, v))
            wins[max(tot, key=tot.get)] += 1
        out[util] = {"scores": base, "best": best, "stability": {o: wins[o] / n for o in opts}, "excluded": excluded}
    return out


@subsystem("means", needs=("hazard",))
def means(cfg, res):
    hz = res["hazard"]
    cur = _mca(tuple(hazard_weights(hz)[c] for c in CRITERIA))
    haz = load_json(DATA / "hazards.json")
    prof = {k: _mca(tuple(hazard_weights(v)[c] for c in CRITERIA)) for k, v in haz.items() if not k.startswith("_")}
    return {"current": cur, "profiles": prof, "criteria": CRITERIA, "options": OPTIONS}


# ----------------------------------------------------- FMEA
FMEA = [  # id, item, failure mode, effect, S,O,D, mitigation (design out > guard > warn), S2,O2,D2
    ("F01", "Wildland-urban interface", "ember ignition of buildings/landscape", "structure loss, casualties", 9, 5, 4,
     "non-combustible roofs/walls, ember screens, defensible ring with low-fuel (succulent/indigenous) planting, ring-main hydrants + ponds, refuge hubs", 9, 2, 3),
    ("F02", "Drainage / flood routes", "overland flow beyond DV<=0.4 m2/s", "injury, property loss", 8, 5, 3,
     "sponge system, flood-route catchment limit, basins, plinth >= 1:100 + 0.5 m", 8, 2, 3),
    ("F03", "Water supply", "multi-year drought exhausts MAR", "potable shortfall", 8, 4, 3,
     "potable reserve in MAR, restrictions protocol, storage + diversification", 8, 2, 2),
    ("F04", "Smart grid / islanding", "grid-forming failure, cell blackout", "loss of power to cell", 7, 4, 4,
     "N+1 grid-forming inverters, black-start batteries, adaptive protection", 7, 2, 3),
    ("F05", "Cell / home storage", "battery thermal event", "fire, toxic release", 9, 3, 4,
     "benign chemistry (NiFe / sodium-ion), segmented fire-rated rooms, venting, BMS", 9, 1, 3),
    ("F06", "Potable / non-potable pipes", "cross-connection", "contamination, illness", 9, 3, 5,
     "colour-coded purple pipe, unique fittings, backflow prevention, commissioning test", 9, 1, 3),
    ("F07", "Digester / biogas", "H2S or methane leak", "toxic / explosive atmosphere", 9, 3, 4,
     "gas detection, ventilation, flare, 50 m siting from dwellings", 9, 1, 3),
    ("F08", "IoT / smart-grid network", "cyber intrusion", "outage, data breach", 8, 4, 5,
     "zero-trust segmentation, open auditable firmware, signed updates, manual local override", 8, 2, 3),
    ("F09", "Streets", "pedestrian-vehicle collision", "injury", 9, 4, 3,
     "design speed 10-30 km/h, 3-leg junctions, shared-surface geometry, lighting", 9, 2, 2),
    ("F10", "Service trough", "electric shock at lid opening", "injury", 9, 3, 4,
     "LV only, IP-rated lids, RCD, segregation from wet strip", 9, 1, 3),
    ("F11", "Buildings + utilities", "seismic damage", "collapse, pipe rupture", 10, 3, 5,
     "system selector by PGA, ties, flexible couplings, no heavy unreinforced earth above threshold", 10, 1, 3),
    ("F12", "Envelope + street furniture", "windstorm / tornado debris", "injury, damage", 9, 3, 4,
     "tie-down load path, hardened shelters <= 6 min walk, secured furniture, windbreak belts", 9, 1, 3),
    ("F13", "Public realm", "heat wave", "heat illness", 7, 5, 3,
     "shade >= 70% of walkable surface, canopy >= 30%, cool surfaces, cooled refuge hubs", 7, 3, 2),
    ("F14", "Greywater / thermal loops", "Legionella growth", "illness", 8, 3, 6,
     "temperature control, treatment, no aerosolising reuse", 8, 1, 4),
    ("F15", "Trees", "limb / tree failure", "injury, line damage", 7, 4, 4,
     "species selection, structural pruning, setbacks, underground lines", 7, 2, 3),
    ("F16", "Slopes", "landslide / slope failure", "loss of structures", 9, 3, 5,
     "slope bands, terraces, deep-rooted cover, drainage", 9, 1, 3),
    ("F17", "Landscape palette", "invasive or high-fuel species", "fire spread, ecological harm", 6, 5, 4,
     "indigenous palette, exclusion list, annual audit", 6, 2, 3),
    ("F18", "Sewer / vacuum line", "blockage or leakage", "contamination, odour", 7, 4, 4,
     "accessible lines, double containment, inspection regime", 7, 2, 3)]


@subsystem("fmea")
def fmea(cfg, res):
    rows = []
    for fid, item, mode, eff, s, o, d, mit, s2, o2, d2 in FMEA:
        rows.append({"id": fid, "item": item, "mode": mode, "effect": eff, "S": s, "O": o, "D": d, "rpn": s * o * d,
                     "mit": mit, "S2": s2, "O2": o2, "D2": d2, "rpn2": s2 * o2 * d2})
    return {"rows": rows, "max_rpn_pre": max(r["rpn"] for r in rows), "max_rpn_post": max(r["rpn2"] for r in rows),
            "mitigated_all": all(r["mit"] for r in rows if r["rpn"] > 100 or r["S"] >= 9),
            "gate": all(r["rpn2"] <= 100 for r in rows) and all(r["mit"] for r in rows if r["S"] >= 9)}
