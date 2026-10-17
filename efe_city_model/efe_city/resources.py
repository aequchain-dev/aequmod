"""efe_city.resources - food, waste, water, energy and thermal balances (per capita, monthly/daily)."""
from __future__ import annotations

import math
import random

from .core import DAYS, EfeError, subsystem


# ------------------------------------------------------------------ food
@subsystem("food", needs=("land", "climate"))
def food(cfg, res):
    f, L = cfg["food"], res["land"]
    P, city = L["pop_cell"], L["city"]
    integ = cfg["agri"]["integrated"]
    prod_cell = L["prod_cell_m2"] / P if integ else 0.0
    wedge_agri = city["wedge_area_m2"] / city["pop"] * f["wedge_agri_share"]
    diet, yld = f["diet_kg_pp"], dict(f["yield_kg_ha"])
    ym = f.get("yield_mode_kg_ha")
    if ym:
        yld["vegetables"] = 1.0 / sum(m["share"] / ym[k] for k, m in f["modes"].items())
    need = {g: diet[g] * 1e4 / yld[g] for g in diet}
    fresh = [g for g in f["priority"] if g in f["fresh_groups"]]
    alloc = {g: 0.0 for g in diet}
    rem_cell, rem_wedge, fresh_cap = prod_cell, wedge_agri, wedge_agri * f["wedge_fresh_share"]
    for g in fresh:
        t = min(need[g], rem_cell)
        alloc[g] += t
        rem_cell -= t
    for g in f["priority"]:
        left = need[g] - alloc[g]
        t = min(left, rem_wedge, fresh_cap) if g in fresh else min(left, rem_wedge)
        if g in fresh:
            fresh_cap -= t
        alloc[g] += t
        rem_wedge -= t
    produced = {g: alloc[g] * yld[g] / 1e4 for g in diet}
    fresh_need = sum(need[g] for g in fresh)
    fresh_ssr = sum(alloc[g] for g in fresh) / fresh_need
    kcal_diet = sum(diet[g] * f["kcal_per_kg"][g] for g in diet)
    kcal_local = sum(produced[g] * f["kcal_per_kg"][g] for g in diet)
    remote_pp = sum(need.values()) - sum(alloc.values())
    r_total = math.sqrt((remote_pp * city["pop"] + city["total_m2"]) / math.pi) / 1000.0
    plant_fresh_kg = produced["vegetables"] + produced["fruit"]
    mode_kwh = sum(m["share"] * m["kwh_kg"] for m in f["modes"].values())
    fresh_kg = sum(produced[g] for g in fresh)
    energy = plant_fresh_kg * mode_kwh + fresh_kg * f["cold_chain_kwh_kg"]
    ng = f["nutrients_g_per_kg"]
    removal_local = [sum(produced[g] * ng[g][i] / 1000.0 for g in ng) for i in range(3)]
    removal_diet = [sum(diet[g] * ng[g][i] / 1000.0 for g in ng) for i in range(3)]
    supply = [x * f["nutrient_recovery"] for x in f["excreta_kg_pp_yr"]]
    return {"need_m2_pp": need, "alloc_m2_pp": alloc, "produced_kg_pp": produced, "prod_cell_pp": prod_cell,
            "wedge_agri_pp": wedge_agri, "fresh_ssr": fresh_ssr, "irrigated_area_pp": alloc["vegetables"] + alloc["fruit"],
            "kcal_diet_pd": kcal_diet / 365.0, "kcal_local_pd": kcal_local / 365.0,
            "kcal_ssr": kcal_local / kcal_diet, "land_need_pp_m2": sum(need.values()),
            "remote_land_pp_m2": remote_pp, "foodshed_radius_km": r_total, "energy_kwh_pp": energy,
            "mode_kwh_kg": mode_kwh, "nutrient_supply_kg_pp": supply, "nutrient_removal_local": removal_local,
            "nutrient_removal_diet": removal_diet,
            "nutrient_closure_local": [supply[i] / removal_local[i] if removal_local[i] else 0 for i in range(3)],
            "nutrient_closure_diet": [supply[i] / removal_diet[i] if removal_diet[i] else 0 for i in range(3)],
            "mushroom_m2_city": f["mushroom_kg_pp"] / f["mushroom_kg_m2_yr"] * city["pop"]}


# ------------------------------------------------------------------ waste
@subsystem("waste")
def waste(cfg, res):
    w = cfg["waste"]
    comp, rec = w["composition"], w["recovery"]
    if abs(sum(comp.values()) - 1.0) > 1e-6:
        raise EfeError("waste composition must sum to 1")
    kg = w["kg_pp_day"] * 365
    stream = {k: kg * v for k, v in comp.items()}
    recovered = {k: stream[k] * rec[k] for k in stream}
    overall = sum(recovered.values()) / kg
    org_t = recovered["organics"] / 1000.0
    biogas = org_t * w["biogas_m3_per_t_org"] + w["blackwater_biogas_m3_pp_day"] * 365
    kwh_th = biogas * cfg["energy"]["biogas_kwh_per_m3"]
    chp = cfg["energy"]["chp"]
    pop = res["land"]["city"]["pop"] if "land" in res else 1.0
    resid_kg = kg - sum(recovered.values())
    return {"kg_pp_yr": kg, "stream_kg_pp": stream, "recovered_kg_pp": recovered, "recovery": overall,
            "residual_kg_pp": resid_kg, "biogas_m3_pp": biogas, "biogas_kwh_pp": kwh_th,
            "chp_kwh_e_pp": kwh_th * cfg["energy"]["chp_eff"] if chp else 0.0,
            "chp_kwh_th_pp": kwh_th * (0.85 - cfg["energy"]["chp_eff"]) if chp else kwh_th * 0.85,
            "residual_t_city_yr": resid_kg * pop / 1000.0,
            "residual_m3_city_yr": resid_kg * pop / w["residual_density_kg_m3"]}


# ------------------------------------------------------------------ water
@subsystem("water", needs=("climate", "land", "food"))
def water(cfg, res):
    w, C, L, F = cfg["water"], res["climate"], res["land"], res["food"]
    mode = w["drainage_mode"]
    if mode not in w["partition"]:
        raise EfeError(f"unknown drainage_mode '{mode}'")
    part = w["partition"][mode]
    P, city = L["pop_cell"], L["city"]
    A = {k: v / P for k, v in L["surface_m2"].items()}
    wedge_pp = city["wedge_area_m2"] / city["pop"]
    irr_area = F["irrigated_area_pp"]
    grey_pp_day = w["grey_lpd"] * w["grey_treat_eff"] / 1000.0 if w["grey_reuse"] else 0.0
    tank_cap, pond_cap = w["tank_m3_pp"], w["pond_m3_pp"]
    pond_area = pond_cap / w["pond_depth_m"] if pond_cap > 0 else 0.0
    cover = w["pond_pv_cover"] if cfg["energy"]["pond_pv"] else 0.0
    rec = w["mar_recovery"]
    sponge = mode == "sponge"
    eff_pp_day = w["black_lpd"] * w["black_treat_eff"] / 1000.0 if (w["grey_reuse"] and w["effluent_reuse"]) else 0.0
    reserve = w["mar_reserve_months"] * w["potable_lpd"] * 30 / 1000.0

    def step(state, m, rain_factor, pot_lpd, irr_factor):
        tank, pond, mar = state
        days, et0 = DAYS[m], C["et0_mm"][m]
        rain = C["p_mm"][m] * rain_factor
        r = rain / 1000.0
        roof_tank = A["roof"] * r * part["roof"]["tank"]
        runoff = A["roof"] * r * part["roof"]["runoff"]
        infil = 0.0
        for cls, area in A.items():
            if cls == "roof":
                continue
            pc = part[cls]
            if cls == "green":
                infil += area * 0.5 * max(0.0, rain - w["kc_green"] * et0) / 1000.0
            else:
                infil += area * pc["infil"] * r
            runoff += area * pc["runoff"] * r
        if sponge:
            swale_inf = runoff * w["swale_infil_frac"]
            to_pond = runoff - swale_inf
            wedge_in = wedge_pp * r * w["wedge_runoff_coeff"]
        else:
            swale_inf = to_pond = wedge_in = 0.0
        pond += to_pond + wedge_in
        evap = min(pond, pond_area * et0 / 1000.0 * (1 - 0.8 * cover))
        pond -= evap
        seep = pond * w["pond_seep_frac"]
        pond -= seep
        spill_pond = max(0.0, pond - pond_cap)
        pond -= spill_pond
        mar_raw = infil + swale_inf + seep
        pot = pot_lpd * days / 1000.0
        npi = w["nonpotable_lpd"] * days / 1000.0
        irr = irr_area * max(0.0, w["kc_veg"] * et0 - w["p_eff"] * rain) / w["irr_eff"] / 1000.0 * irr_factor
        grey = grey_pp_day * days
        eff = eff_pp_day * days
        avail = tank + roof_tank
        from_tank = min(pot, avail)
        tank = avail - from_tank
        spill_tank = max(0.0, tank - tank_cap)
        tank -= spill_tank
        mar_raw += spill_tank
        mar += mar_raw * rec
        mar_loss = mar_raw * (1 - rec)
        need = pot - from_tank
        mar_pot = min(need, mar)
        mar -= mar_pot
        ext_pot = need - mar_pot
        g1 = min(npi, grey)
        need = npi - g1
        p1 = min(need, pond)
        pond -= p1
        need -= p1
        m1 = min(need, max(0.0, mar - reserve))
        mar -= m1
        ext_np = need - m1
        g2 = min(irr, grey - g1 + eff)
        need = irr - g2
        p2 = min(need, pond)
        pond -= p2
        need -= p2
        m2 = min(need, max(0.0, mar - reserve))
        mar -= m2
        ext_irr = need - m2
        row = {"m": m, "rain_mm": rain, "pot": pot, "np": npi, "irr": irr, "ext_pot": ext_pot, "ext_np": ext_np,
               "ext_irr": ext_irr, "tank": tank, "pond": pond, "mar": mar, "grey_used": g1 + g2,
               "in_store": roof_tank + infil + swale_inf + to_pond + wedge_in,
               "out_store": from_tank + mar_pot + p1 + m1 + p2 + m2 + evap + spill_pond + mar_loss,
               "lost_runoff": 0.0 if sponge else runoff, "pond_evap": evap, "pond_spill": spill_pond}
        return (tank, pond, mar), row

    state = (0.0, 0.0, 0.0)
    for _ in range(3):                                   # spin-up
        for m in range(12):
            state, _ = step(state, m, 1.0, w["potable_lpd"], 1.0)
    s0 = sum(state)
    rows = []
    for m in range(12):
        state, row = step(state, m, 1.0, w["potable_lpd"], 1.0)
        rows.append(row)
    ds = sum(state) - s0
    tot = lambda k: sum(r[k] for r in rows)
    closure = tot("in_store") - tot("out_store") - ds
    dstate, drows = state, []
    hz = res["hazard"] if "hazard" in res else {"drought_factor": 0.65, "drought_years": 3}
    for _ in range(int(hz["drought_years"])):
        for m in range(12):
            dstate, row = step(dstate, m, hz["drought_factor"], w["drought_restrict_lpd"], 1 - w["drought_irrigation_cut"])
            drows.append(row)
    d_pot = sum(r["pot"] for r in drows)
    d_ext = sum(r["ext_pot"] for r in drows)
    first_short = next((i for i, r in enumerate(drows) if r["ext_pot"] > 0.05 * r["pot"]), None)
    pot_t, np_t, irr_t = tot("pot"), tot("np"), tot("irr")
    ext = {"pot": tot("ext_pot"), "np": tot("ext_np"), "irr": tot("ext_irr")}
    energy = w["treat_kwh_m3"] * pot_t + w["pump_kwh_m3"] * irr_t + 0.3 * tot("grey_used")
    return {"rows": rows, "pot_m3_pp": pot_t, "np_m3_pp": np_t, "irr_m3_pp": irr_t, "ext_m3_pp": ext,
            "ssr_potable": 1 - ext["pot"] / pot_t if pot_t else 1.0,
            "ssr_nonpotable": 1 - ext["np"] / np_t if np_t else 1.0,
            "ssr_irrigation": 1 - ext["irr"] / irr_t if irr_t else 1.0,
            "ssr_total": 1 - sum(ext.values()) / (pot_t + np_t + irr_t),
            "rain_cell_m3_pp": sum(A.values()) * sum(C["p_mm"]) / 1000.0, "roof_m2_pp": A["roof"],
            "lost_runoff_m3_pp": tot("lost_runoff"), "pond_evap_m3_pp": tot("pond_evap"),
            "peak_tank": max(r["tank"] for r in rows), "peak_pond": max(r["pond"] for r in rows),
            "peak_mar": max(r["mar"] for r in rows), "closure_m3_pp": closure,
            "closure_rel": closure / max(tot("in_store"), 1e-9), "energy_kwh_pp": energy,
            "drought": {"years": int(hz["drought_years"]), "factor": hz["drought_factor"], "unmet_pot_pct": 100 * d_ext / d_pot,
                        "first_shortfall_month": first_short, "mar_end": drows[-1]["mar"]},
            "irrigated_area_pp": irr_area, "pond_area_pp": pond_area, "grey_pp_yr": grey_pp_day * 365}


# ------------------------------------------------------------------ energy
def daily_sim(gen_m, dem_m, chp_day, batt, eta_rt, dayfrac, sigma, rho, seed):
    """Day-resolved balance with stochastic cloudiness, day/night load split and a battery."""
    rng = random.Random(seed)
    eta = math.sqrt(eta_rt)
    z, soc = 0.0, 0.5 * batt
    soc0 = soc
    T = dict(gen=0.0, load=0.0, imp=0.0, exp=0.0, loss=0.0, chp=0.0, direct=0.0, cin=0.0, dis=0.0)
    monthly, run, max_run, lold = [], 0, 0, 0
    for m in range(12):
        n = DAYS[m]
        mult = []
        for _ in range(n):
            z = rho * z + math.sqrt(1 - rho * rho) * rng.gauss(0, 1)
            mult.append(min(1.8, max(0.1, 1 + sigma * z)))
        s = sum(mult) / n
        mult = [x / s for x in mult]
        M = dict(gen=0.0, load=0.0, imp=0.0, exp=0.0)
        for d in range(n):
            G, L = gen_m[m] / n * mult[d], dem_m[m] / n
            chp = min(chp_day, L)
            netL = L - chp
            Ld, Ln = netL * dayfrac, netL * (1 - dayfrac)
            direct = min(G, Ld)
            surplus = G - direct
            cin = min(surplus, (batt - soc) / eta) if batt > 0 else 0.0
            soc += cin * eta
            export = surplus - cin
            need = Ld - direct
            dis1 = min(need, soc * eta) if batt > 0 else 0.0
            soc -= dis1 / eta
            unmet = need - dis1
            dis2 = min(Ln, soc * eta) if batt > 0 else 0.0
            soc -= dis2 / eta
            unmet += Ln - dis2
            dis = dis1 + dis2
            loss = cin * (1 - eta) + dis * (1 / eta - 1)
            for k, v in (("gen", G), ("load", L), ("imp", unmet), ("exp", export), ("loss", loss), ("chp", chp),
                         ("direct", direct), ("cin", cin), ("dis", dis)):
                T[k] += v
            M["gen"] += G
            M["load"] += L
            M["imp"] += unmet
            M["exp"] += export
            if unmet > 1e-9:
                lold += 1
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        monthly.append(M)
    closure = T["gen"] + T["imp"] + T["chp"] - (T["load"] + T["exp"] + T["loss"] + (soc - soc0))
    return T, monthly, lold, max_run, closure


@subsystem("energy", needs=("climate", "land", "solar", "food", "transport", "water", "waste"))
def energy(cfg, res):
    e, C, L, S = cfg["energy"], res["climate"], res["land"], res["solar"]
    P, city = L["pop_cell"], L["city"]
    kw = e["module_kwp_m2"]
    wedge_agri = city["wedge_area_m2"] / city["pop"] * cfg["food"]["wedge_agri_share"]
    pond_pp = cfg["water"]["pond_m3_pp"] / cfg["water"]["pond_depth_m"] if cfg["water"]["pond_m3_pp"] > 0 else 0.0
    areas = {"roof": L["footprint_m2"] * e["roof_usable"] / P,
             "canopy": e["canopy_width_m"] * L["lengths_m"]["seam"] / P,
             "agri_pv": wedge_agri * e["agri_pv_fraction"] * e["agri_pv_gcr"],
             "floating": pond_pp * cfg["water"]["pond_pv_cover"] if e["pond_pv"] else 0.0}
    src = {"roof": (S["monthly"]["roof"], 1.0), "canopy": (S["monthly"]["canopy"], 1.0),
           "agri_pv": (S["monthly"]["roof"], e["agri_pv_factor"]), "floating": (S["monthly"]["canopy"], e["floating_factor"])}
    place, gen_m = [], [0.0] * 12
    for k, a in areas.items():
        kwp = a * kw
        y, fac = src[k]
        mon = [kwp * y[m] * fac for m in range(12)]
        gen_m = [gen_m[m] + mon[m] for m in range(12)]
        place.append({"name": k, "m2_pp": a, "kwp_pp": kwp, "kwh_kwp": sum(y) * fac, "kwh_pp": sum(mon)})
    base = dict(e["demand_kwh_pp"])
    base["agri_processing"] = res["food"]["energy_kwh_pp"]
    base["mobility"] = res["transport"]["energy_kwh_pp"]
    base["water_systems"] = res["water"]["energy_kwh_pp"]
    D = sum(base.values()) * e.get("demand_factor", 1.0)
    shape = [1 + e["heating_k"] * max(0.0, e["heating_base_c"] - t) for t in C["tmean_c"]]
    wts = [shape[m] * DAYS[m] for m in range(12)]
    dem_m = [D * wts[m] / sum(wts) for m in range(12)]
    chp_pp = res["waste"]["chp_kwh_e_pp"]
    T, mon, lold, max_run, closure = daily_sim(gen_m, dem_m, chp_pp / 365.0, e["storage_kwh_pp"], e["rt_eff"],
                                               e["day_load_fraction"], e["cloud_sigma"], e["cloud_rho"], e["seed"])
    hh = cfg["geometry"]["household_size"]
    roof_kwp_pp = areas["roof"] * kw
    roof_y = sum(S["monthly"]["roof"])
    equity = []
    for st in (1, 2, 3, 4, 5):
        kwh = cfg["geometry"]["gfa_per_capita_m2"] / st * e["roof_usable"] * kw * roof_y
        equity.append({"storeys": st, "roof_kwh_pp": kwh, "ratio": kwh / D})
    canopy_kwh = place[1]["kwh_pp"]
    return {"placements": place, "kwp_pp": sum(p["kwp_pp"] for p in place), "gen_kwh_pp": sum(gen_m),
            "demand_kwh_pp": D, "demand_split": base, "monthly": [{"gen": gen_m[m], "dem": dem_m[m], "imp": mon[m]["imp"],
            "exp": mon[m]["exp"]} for m in range(12)], "chp_kwh_e_pp": chp_pp,
            "ssr": 1 - T["imp"] / T["load"], "import_kwh_pp": T["imp"], "export_kwh_pp": T["exp"],
            "loss_kwh_pp": T["loss"], "lold_days": lold, "max_import_run_days": max_run, "closure_kwh_pp": closure,
            "storage_kwh_pp": e["storage_kwh_pp"], "autonomy_h": e["storage_kwh_pp"] / (D / 8760.0),
            "hen": {"pv_kwp": roof_kwp_pp * hh, "battery_kwh": e["storage_kwh_pp"] * e["storage_home_fraction"] * hh,
                    "cell_battery_mwh": e["storage_kwh_pp"] * (1 - e["storage_home_fraction"]) * P / 1000.0,
                    "inverter_kw": roof_kwp_pp * hh / 1.2},
            "equity": equity, "canopy_kwh_pp": canopy_kwh,
            "opt_tilt": S["opt_tilt"], "opt_yield": S["opt_yield"], "facade_yield": sum(S["monthly"]["facade"])}


# ------------------------------------------------------------------ thermal
@subsystem("thermal", needs=("land", "climate"))
def thermal(cfg, res):
    t, L, S = cfg["thermal"], res["land"], res["land"]["surface_m2"]
    alb = {"roof": t["albedo_roof"], "green": 0.20, "permeable_walk": 0.35, "permeable_street": 0.35, "ribbon": 0.35}
    total = sum(S.values())
    walk = S["permeable_walk"] + S["ribbon"]
    shade = (S["permeable_walk"] * t["tree_shade_walk"] + S["ribbon"] * 1.0) / walk
    pv_canopy = cfg["energy"]["canopy_width_m"] * L["lengths_m"]["seam"]
    cover = (S["green"] * t["tree_cover_green"] + pv_canopy) / L["hex"]["area_m2"]
    green = S["green"] / total
    return {"mean_albedo": sum(S[k] * alb[k] for k in S) / total, "shade_fraction": shade, "canopy_cover": cover,
            "green_fraction": green, "et_cooling_w_m2": t["et_mm_day_green"] * 2.45e6 / 86400.0 * green}
