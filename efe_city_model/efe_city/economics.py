"""efe_city.economics - EFE economics layer: capex envelope, external cost per member, contribution bound,
internalization priority. Planning-grade unit costs; NOT financial advice."""
from __future__ import annotations

from .core import subsystem


@subsystem("economics", needs=("land", "water", "energy", "food", "waste", "transport", "synergy", "facilities", "thermal"))
def economics(cfg, res):
    e, g, L = cfg["economics"], cfg["geometry"], res["land"]
    P, S = L["pop_cell"], L["surface_m2"]
    W, E, F, T, Y = res["water"], res["energy"], res["food"], res["transport"], res["synergy"]
    hh = g["household_size"]
    capex = {}
    capex["buildings"] = (g["gfa_per_capita_m2"] - g["nonres_gfa_per_capita_m2"]) * e["usd_m2"]["res"] + \
        g["nonres_gfa_per_capita_m2"] * e["usd_m2"]["nonres"]
    capex["surfaces"] = sum(S[k] * e["usd_m2"][k] for k in ("permeable_street", "permeable_walk", "ribbon", "green")) / P
    capex["corridors_utilities"] = Y["corridor_cost_usd_pp"]
    key = {"roof": "roof", "canopy": "canopy", "agri_pv": "agri", "floating": "floating"}
    capex["solar"] = sum(p["kwp_pp"] * e["usd_kwp"][key[p["name"]]] for p in E["placements"])
    capex["storage"] = E["storage_kwh_pp"] * e["usd_kwh_storage"]
    w = cfg["water"]
    capex["water_systems"] = w["tank_m3_pp"] * e["usd_m3"]["tank"] + w["pond_m3_pp"] * e["usd_m3"]["pond"] + \
        e["wetland_ad_usd_pp"] + e["aequaqua_usd_dwelling"] / hh
    tun_share = cfg["food"]["modes"]["tunnel"]["share"]
    gh_m2 = F["produced_kg_pp"]["vegetables"] * tun_share / cfg["food"]["yield_mode_kg_ha"]["tunnel"] * 1e4
    capex["agriculture"] = gh_m2 * e["greenhouse_usd_m2"] + F["irrigated_area_pp"] * e["irrigation_usd_m2"] + \
        F["mushroom_m2_city"] / L["city"]["pop"] * 500.0
    capex["mobility"] = T["fleet_shuttles"] * e["shuttle_usd"] / L["city"]["pop"] + e["trikes_pp"] * e["trike_usd"]
    capex["digital_waste"] = e["digital_usd_pp"] + e["waste_machinery_usd_pp"]
    direct = sum(capex.values())
    capex["contingency"] = direct * e["contingency"]
    total = direct + capex["contingency"]
    diet_kg = sum(cfg["food"]["diet_kg_pp"].values())
    local_kg = sum(F["produced_kg_pp"].values())
    ext = {"food_imports": max(0.0, diet_kg - local_kg) * e["food_import_usd_kg"],
           "energy_imports": E["import_kwh_pp"] * e["grid_usd_kwh"],
           "bulk_water": sum(W["ext_m3_pp"].values()) * e["bulk_water_usd_m3"],
           "maintenance_parts": total * e["parts_fraction_of_capex"],
           "compliance_it": e["compliance_it_usd_pp"],
           "imported_capital_goods": total * e["imported_capital_share"] / e["asset_life_yr"]}
    ext_total = sum(ext.values())
    cap = e["contribution_cap"]
    scen = [{"revenue_pp": r, "rate": ext_total / r, "ok": ext_total / r <= cap} for r in e["revenue_scenarios_usd_pp"]]
    prio = sorted(ext.items(), key=lambda kv: -kv[1])
    return {"capex": capex, "capex_pp": total, "external": ext, "external_cost_pp": ext_total,
            "required_revenue_pp": ext_total / cap, "scenarios": scen, "priority": prio,
            "vs_ever": total / e["evers_capex_usd_pp"], "city_capex_musd": total * L["city"]["pop"] / 1e6,
            "equality_invariant": "Member_Value = Total_Treasury / Total_Members"}
