"""efe_city.synergy - interaction engine (23 subsystems), unified-corridor (AEQUSPINE) quantification, city metabolism."""
from __future__ import annotations

import math

from .core import EfeError, subsystem

# code: (label, zones, outputs, inputs, data_out, data_in)  -- comma-separated tokens
SUBS = {
    "ROAD": ("Roads & mobility surface", "street", "mobility", "power,stone,structure,alerts", "traffic", "signal"),
    "SIGN": ("Demarcation, signage, street code", "street,walk,pole", "rules,signal", "power,stone", "", ""),
    "PAVE": ("Paving, walkways, traction", "street,walk,node", "infiltration", "stone,waste_dry", "surface_state", ""),
    "WATR": ("Potable water supply", "WET", "water_pot", "water_rain,power,water_treated", "flow", "demand"),
    "DRAN": ("Drainage & waterways", "swale,pond,verge", "water_rain,habitat,cooling", "infiltration", "level", "forecast"),
    "SEWR": ("Sanitation / blackwater", "WET", "water_black", "blackwater_src,water_treated", "flow", ""),
    "GREY": ("Greywater reuse", "WET,plot", "water_treated", "water_grey,power", "", ""),
    "POWR": ("Electricity & smart grid", "TROUGH,canopy,roof,pole", "power", "biogas", "load", "price,forecast"),
    "THRM": ("Thermal management", "TROUGH,roof", "heat,cooling", "power,biogas,water_grey,cooling", "temp", ""),
    "DATA": ("Internet & data", "TROUGH,pole,node", "data", "power",
             "", "traffic,flow,level,load,temp,soil,waste_level,status,occupancy,surface_state"),
    "LITE": ("Lighting", "pole,street,walk,canopy", "light", "power", "occupancy", "traffic,load"),
    "AGRI": ("Agriculture & food", "verge,plot,field,roof", "food,waste_org,habitat,cooling",
             "water_treated,nutrients,water_rain,heat,power", "soil", "forecast"),
    "FAUN": ("Fauna & habitat", "verge,swale,pond,field", "pollination", "habitat,water_rain", "", ""),
    "WAST": ("Waste handling & digestion", "node", "biogas,nutrients,stone,waste_dry", "waste_org,waste_dry,water_black",
             "waste_level", ""),
    "PUBL": ("Public facilities & ablutions", "node,plot", "blackwater_src,water_grey,waste_org,shelter",
             "water_pot,power,data,food,alerts", "occupancy", ""),
    "TRAN": ("Public transport", "street", "mobility", "power", "traffic", "signal"),
    "BLDG": ("Buildings & structures", "plot,roof,node", "blackwater_src,water_grey,waste_org,waste_dry",
             "water_pot,power,data,stone,food,wind_shelter", "load", ""),
    "FORE": ("Forestation & landscape", "verge,swale,field", "shade,habitat,cooling,wind_shelter,waste_org",
             "water_treated,water_rain", "", ""),
    "BRDG": ("Bridges & crossings", "swale,street", "structure", "stone", "", ""),
    "MACH": ("Machinery & maintenance", "street,walk,TROUGH,WET", "service", "power", "", "status"),
    "SOUN": ("Sound & acoustics", "verge,swale", "sound_masking", "habitat", "", ""),
    "TERR": ("Terrain & earthworks", "street,plot,field,swale", "slope_info", "", "", ""),
    "HAZD": ("Weather & hazard response", "street,plot,field,roof,verge,swale", "alerts,shelter", "data", "status", "")}
CODE2 = {"ROAD": "RD", "SIGN": "SG", "PAVE": "PV", "WATR": "WT", "DRAN": "DR", "SEWR": "SW", "GREY": "GW", "POWR": "PW",
         "THRM": "TH", "DATA": "DT", "LITE": "LT", "AGRI": "AG", "FAUN": "FA", "WAST": "WS", "PUBL": "PB", "TRAN": "TR",
         "BLDG": "BL", "FORE": "FO", "BRDG": "BG", "MACH": "MC", "SOUN": "SN", "TERR": "TE", "HAZD": "HZ"}
CONFLICTS = [  # a, b, reason, mitigation rule
    ("WATR", "SEWR", "cross-contamination", "potable above sewer, >=0.3 m vertical and >=1.0 m horizontal separation"),
    ("WATR", "POWR", "leak vs electrocution", "separate dry TROUGH and wet strip; LV only in trough"),
    ("SEWR", "AGRI", "pathogens", "only aged/treated digestate and effluent; drip, no raw application on edibles"),
    ("FORE", "WATR", "root intrusion", "tree-free wet strip, root barriers"),
    ("FORE", "POWR", "shading of PV, limb failure", "colonnade-first siting; underground lines; trees outside canopy footprint"),
    ("POWR", "AGRI", "PV shading of crops", "agri-PV spec: GCR <= 0.35, clearance >= 3.5 m, shade-tolerant crops"),
    ("ROAD", "FAUN", "wildlife strike, noise", "<=30 km/h, crossings, dark corridors"),
    ("LITE", "FAUN", "light pollution", "amber <= 2200 K, full cut-off, dimming, dark waterway corridors"),
    ("FORE", "HAZD", "fuel load", "fire-smart palette, ring spacing, ember screens"),
    ("DRAN", "BLDG", "flood damage", "plinth >= 1:100 + 0.5 m, setbacks, flood-route DV limit"),
    ("DRAN", "ROAD", "street flow depth x velocity", "catchment limit per overland route (DV <= 0.4 m2/s)"),
    ("THRM", "GREY", "Legionella", "temperature control, no aerosolising reuse"),
    ("AGRI", "WAST", "odour, pests", "enclosed digestion, siting, buffers"),
    ("BRDG", "DRAN", "flow obstruction", "clear-span over floodway, no in-stream piers, freeboard"),
    ("SOUN", "ROAD", "traffic noise", "<=30 km/h, soft surfaces, setbacks, planted buffers"),
    ("PAVE", "FORE", "root heave", "structural soil / root cells, species selection"),
    ("MACH", "POWR", "maintenance access vs live parts", "lockable lids, isolation, trained crews")]

TRENCH = {"power": (0.6, 1.0, 40.0), "data": (0.4, 0.6, 12.0), "potable": (0.6, 1.2, 55.0),
          "sewer": (1.0, 2.0, 90.0), "storm": (1.2, 2.0, 110.0), "nonpotable": (0.5, 1.0, 45.0)}
UNIFIED = {"trough": (1.2, 0.9, 137.0), "wet_strip": (1.2, 1.8, 190.0)}   # width, depth, USD/m excl. excavation
ACCESS = {"separate": {"power": 0, "data": 0, "potable": 0, "sewer": 0, "storm": 0.15, "nonpotable": 0},
          "unified": {"power": 1, "data": 1, "potable": 0.6, "sewer": 0.6, "storm": 1.0, "nonpotable": 0.6}}


def _tokens(s):
    return {t for t in s.split(",") if t}


def _zones(code, mode):
    out = set()
    for t in _tokens(SUBS[code][1]):
        if t in ("WET", "TROUGH"):
            out.add(t.lower() if mode == "unified" else f"{t.lower()}_{code}")
        else:
            out.add(t)
    return out


def interaction_matrix(mode):
    codes = list(SUBS)
    conf = {frozenset((a, b)): (r, m) for a, b, r, m in CONFLICTS}
    cells, pairs = {}, []
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            s = len(_zones(a, mode) & _zones(b, mode))
            f = len(_tokens(SUBS[a][2]) & _tokens(SUBS[b][3])) + len(_tokens(SUBS[b][2]) & _tokens(SUBS[a][3]))
            n = len(_tokens(SUBS[a][4]) & _tokens(SUBS[b][5])) + len(_tokens(SUBS[b][4]) & _tokens(SUBS[a][5]))
            c = frozenset((a, b)) in conf
            sym = "X" if c else "B" if (f and s) else "F" if f else "S" if s else "i" if n else "."
            cells[(a, b)] = cells[(b, a)] = sym
            pairs.append({"a": a, "b": b, "S": s, "F": f, "I": n, "C": c, "score": 3 * f + 2 * s + n, "sym": sym})
    realised = sum(1 for p in pairs if p["F"] or p["S"])
    zone_groups = {}
    for code in codes:
        for z in _zones(code, mode):
            zone_groups.setdefault(z, []).append(code)
    return {"codes": codes, "cells": cells, "pairs": pairs, "realised": realised,
            "conflicts": CONFLICTS, "zone_groups": zone_groups,
            "top": sorted(pairs, key=lambda p: -p["score"])[:15]}


@subsystem("synergy", needs=("land",))
def synergy(cfg, res):
    L, e = res["land"], cfg["economics"]
    mode = cfg["corridors"]["mode"]
    if mode not in ("separate", "unified"):
        raise EfeError(f"unknown corridors.mode '{mode}'")
    P = L["pop_cell"]
    net_len = L["lengths_m"]["seam"] + L["lengths_m"]["lane"] + 0.5 * L["lengths_m"]["path"]
    sep_vol = sum(w * d for w, d, _ in TRENCH.values())
    uni_vol = sum(w * d for w, d, _ in UNIFIED.values())
    sep_item = sum(c for _, _, c in TRENCH.values())
    uni_item = sum(c for _, _, c in UNIFIED.values())
    vol_pm, item_pm = (uni_vol, uni_item) if mode == "unified" else (sep_vol, sep_item)
    trench_m3_pp = vol_pm * net_len / P
    leg = cfg["legacy"]
    deep = cfg["underground"]["mode"] == "deep"
    tunnel_m3_pp = leg["tunnel_km"] * 1000 * math.pi * (leg["tunnel_bore_m"] / 2) ** 2 / leg["pop"] if deep else 0.0
    layout = cfg["geometry"]["layout"]
    if layout == "hex_cellular":
        corridor_pp = net_len / P
        section_types = 3
    else:
        dens = cfg["geometry"]["gross_density_p_ha"]
        corridor_pp = (2e4 / leg["block_m"]) / dens + leg["arterial_m_pp"]
        section_types = 5
    trench_types = 2 if mode == "unified" else 6
    complexity = trench_types + section_types + (4 if deep else 0)
    acc = ACCESS[mode]
    inspect = sum(acc.values()) / len(acc)
    cost_pp = (vol_pm * e["excavation_usd_m3"] + item_pm) * net_len / P + (leg["tunnel_km"] * 60e6 / leg["pop"] if deep else 0.0)
    mat = interaction_matrix(mode)
    base_cells = 1 if layout == "hex_cellular" else leg["growth_step_pop"] / P
    return {"mode": mode, "net_len_cell_m": net_len, "corridor_m_pp": corridor_pp, "trench_m3_per_m": vol_pm,
            "sep_m3_per_m": sep_vol, "uni_m3_per_m": uni_vol, "trench_m3_pp": trench_m3_pp, "tunnel_m3_pp": tunnel_m3_pp,
            "excavation_m3_pp": trench_m3_pp + tunnel_m3_pp, "trench_types": trench_types, "section_types": section_types,
            "complexity": complexity, "inspectable_fraction": inspect, "corridor_cost_usd_pp": cost_pp,
            "saving_excavation_pct": 100 * (1 - uni_vol / sep_vol), "saving_openings_pct": 100 * (1 - 2 / 6),
            "growth_step_pop": P if layout == "hex_cellular" else leg["growth_step_pop"],
            "matrix": mat, "synergy_pairs": mat["realised"], "matrix_separate": interaction_matrix("separate")["realised"]}


@subsystem("metabolism", needs=("water", "energy", "food", "waste", "land"))
def metabolism(cfg, res):
    W, E, F, S = res["water"], res["energy"], res["food"], res["waste"]
    return {"water_m3_pp": {"rain_on_cell": W["rain_cell_m3_pp"], "potable": W["pot_m3_pp"], "nonpotable": W["np_m3_pp"],
                            "irrigation": W["irr_m3_pp"], "grey_reclaimed_yr": W["grey_pp_yr"],
                            "external": sum(W["ext_m3_pp"].values()), "lost_runoff": W["lost_runoff_m3_pp"]},
            "energy_kwh_pp": {"generation": E["gen_kwh_pp"], "demand": E["demand_kwh_pp"], "chp": E["chp_kwh_e_pp"],
                              "export": E["export_kwh_pp"], "import": E["import_kwh_pp"], "losses": E["loss_kwh_pp"]},
            "nutrients_kg_pp": {"supply_NPK": F["nutrient_supply_kg_pp"], "removal_local_NPK": F["nutrient_removal_local"]},
            "waste_kg_pp": {"generated": S["kg_pp_yr"], "recovered": sum(S["recovered_kg_pp"].values()),
                            "residual": S["residual_kg_pp"]},
            "food_kg_pp": {"local_produced": sum(F["produced_kg_pp"].values()), "diet": sum(cfg["food"]["diet_kg_pp"].values())}}
