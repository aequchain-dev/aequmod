"""efe_city.site - climate/hazard profiles and solar geometry (Liu-Jordan / Erbs monthly model)."""
from __future__ import annotations

import math

from .core import DATA, DAYS, MID_DAY, EfeError, load_json, subsystem

R = math.radians


def declination(n):
    return 23.45 * math.sin(R(360.0 * (284 + n) / 365.0))


def sunset_angle(phi, dec):
    x = -math.tan(R(phi)) * math.tan(R(dec))
    return math.degrees(math.acos(max(-1.0, min(1.0, x))))


def h0_daily(phi, n):
    """Extraterrestrial horizontal irradiation, kWh/m2/day."""
    d = declination(n)
    ws = sunset_angle(phi, d)
    e0 = 1 + 0.033 * math.cos(R(360.0 * n / 365.0))
    return (24 / math.pi) * 1.367 * e0 * (
        math.cos(R(phi)) * math.cos(R(d)) * math.sin(R(ws)) + R(ws) * math.sin(R(phi)) * math.sin(R(d)))


def diffuse_fraction(kt, ws):
    if ws <= 81.4:
        f = 1.391 - 3.560 * kt + 4.189 * kt ** 2 - 2.137 * kt ** 3
    else:
        f = 1.311 - 3.022 * kt + 3.427 * kt ** 2 - 1.821 * kt ** 3
    return max(0.05, min(1.0, f))


def tilted_daily(phi, n, h, tilt, albedo=0.2):
    """Mean daily irradiation on an equator-facing plane (isotropic sky), kWh/m2/day."""
    d = declination(n)
    ws = sunset_angle(phi, d)
    h0 = h0_daily(phi, n)
    kt = max(0.05, min(0.85, h / h0)) if h0 > 0 else 0.5
    hd = h * diffuse_fraction(kt, ws)
    hb = h - hd
    pe = phi - tilt if phi >= 0 else phi + tilt          # hemisphere-aware effective latitude
    x = -math.tan(R(pe)) * math.tan(R(d))
    wst = min(ws, math.degrees(math.acos(max(-1.0, min(1.0, x)))))
    num = math.cos(R(pe)) * math.cos(R(d)) * math.sin(R(wst)) + R(wst) * math.sin(R(pe)) * math.sin(R(d))
    den = math.cos(R(phi)) * math.cos(R(d)) * math.sin(R(ws)) + R(ws) * math.sin(R(phi)) * math.sin(R(d))
    rb = max(0.0, num / den) if den > 1e-9 else 0.0
    return hb * rb + hd * (1 + math.cos(R(tilt))) / 2 + h * albedo * (1 - math.cos(R(tilt))) / 2


def pv_specific_yield(clim, tilt, pr=0.8):
    """Monthly AC-side yield, kWh per kWp, for an equator-facing array."""
    return [tilted_daily(clim["lat"], MID_DAY[m], clim["ghi_kwh_m2_d"][m], tilt) * DAYS[m] * pr for m in range(12)]


@subsystem("climate")
def _climate(cfg, res):
    data = load_json(DATA / "climates.json")
    key = cfg["site"]["climate"]
    if key not in data:
        raise EfeError(f"unknown climate '{key}'; available: {[k for k in data if not k.startswith('_')]}")
    c = dict(data[key])
    sf = cfg["site"]
    c["p_mm"] = [x * sf.get("rain_factor", 1.0) for x in c["p_mm"]]
    c["ghi_kwh_m2_d"] = [x * sf.get("ghi_factor", 1.0) for x in c["ghi_kwh_m2_d"]]
    return c


@subsystem("hazard")
def _hazard(cfg, res):
    data = load_json(DATA / "hazards.json")
    key = cfg["site"]["hazard_profile"]
    if key not in data:
        raise EfeError(f"unknown hazard profile '{key}'")
    return dict(data[key])


@subsystem("solar", needs=("climate",))
def _solar(cfg, res):
    c, e = res["climate"], cfg["energy"]
    pr = e["performance_ratio"]
    annual = {t: sum(pv_specific_yield(c, t, pr)) for t in range(0, 91, 5)}
    best = max(annual, key=annual.get)
    return {"lat": c["lat"], "opt_tilt": best, "opt_yield": annual[best], "yield_by_tilt": annual,
            "annual_h_kwh_m2": sum(c["ghi_kwh_m2_d"][m] * DAYS[m] for m in range(12)),
            "monthly": {"roof": pv_specific_yield(c, e["roof_tilt"], pr),
                        "canopy": pv_specific_yield(c, e["canopy_tilt"], pr),
                        "facade": pv_specific_yield(c, 90, pr),
                        "optimum": pv_specific_yield(c, best, pr)}}
