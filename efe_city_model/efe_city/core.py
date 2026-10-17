"""efe_city.core - config loading, subsystem registry, small math helpers (stdlib only)."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

PKG = Path(__file__).resolve().parent
DATA = PKG / "data"
SQ3 = math.sqrt(3.0)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MID_DAY = [17, 47, 75, 105, 135, 162, 198, 228, 258, 288, 318, 344]


class EfeError(Exception):
    """Invalid configuration or infeasible design. Fail loudly, never silently."""


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def deep_update(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def get(d, path):
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, (list, tuple)) and part.lstrip("-").isdigit():
            cur = cur[int(part)]
        else:
            raise EfeError(f"missing key '{path}' (stopped at '{part}')")
    return cur


def set_path(d, path, value):
    cur = d
    parts = path.split(".")
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def parse_value(s):
    try:
        return json.loads(s)
    except ValueError:
        return s


def apply_overrides(cfg, items):
    """items: iterable of 'dotted.key=json_value' strings."""
    cfg = copy.deepcopy(cfg)
    for it in items or ():
        if "=" not in it:
            raise EfeError(f"override must be key=value, got '{it}'")
        k, v = it.split("=", 1)
        set_path(cfg, k.strip(), parse_value(v.strip()))
    return cfg


def load_config(path=None, overrides=()):
    base = load_json(path or PKG / "configs" / "reference_cape_town.json")
    return apply_overrides(base, overrides)


def gini(xs):
    xs = sorted(xs)
    n, s = len(xs), sum(xs)
    if n == 0 or s == 0:
        return 0.0
    cum = sum(i * x for i, x in enumerate(xs, 1))
    return (2.0 * cum) / (n * s) - (n + 1.0) / n


def percentile(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100.0
    f = int(math.floor(k))
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def clip(x, lo, hi):
    return max(lo, min(hi, x))


# ---- subsystem registry: each subsystem is fn(cfg, res) -> dict, with declared dependencies ----
SUBSYSTEMS = {}


def subsystem(name, needs=()):
    def deco(fn):
        SUBSYSTEMS[name] = (fn, tuple(needs))
        return fn
    return deco


def run_all(cfg, only=None):
    """Run every registered subsystem (or `only`) in dependency order; returns results dict."""
    from . import site, urban, resources, resilience, synergy, economics  # noqa: F401  (registers)
    res, done = {}, set()

    def visit(name, stack=()):
        if name in done:
            return
        if name in stack:
            raise EfeError(f"dependency cycle: {' -> '.join(stack + (name,))}")
        if name not in SUBSYSTEMS:
            raise EfeError(f"unknown subsystem '{name}'")
        fn, needs = SUBSYSTEMS[name]
        for n in needs:
            visit(n, stack + (name,))
        res[name] = fn(cfg, res)
        done.add(name)

    for n in (only or list(SUBSYSTEMS)):
        visit(n)
    return res
