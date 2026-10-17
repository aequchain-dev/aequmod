"""Unit tests for efe_city (stdlib unittest). Run: python -m unittest discover -s tests"""
import copy
import math
import unittest

from efe_city import core, evaluate as ev, report, resilience, site, synergy, urban, analysis
from efe_city.core import EfeError, apply_overrides, gini, load_config, percentile, run_all


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.res = run_all(cls.cfg)
        cls.ev = ev.evaluate(cls.cfg)


class TestCore(Base):
    def test_gini(self):
        self.assertAlmostEqual(gini([1.0] * 10), 0.0)
        self.assertGreater(gini([0.0] * 9 + [10.0]), 0.85)

    def test_percentile(self):
        self.assertAlmostEqual(percentile(list(range(101)), 95), 95.0)

    def test_overrides(self):
        c = apply_overrides(self.cfg, ["geometry.gross_density_p_ha=80", 'site.climate="lisbon"'])
        self.assertEqual(c["geometry"]["gross_density_p_ha"], 80)
        self.assertEqual(c["site"]["climate"], "lisbon")
        self.assertEqual(self.cfg["geometry"]["gross_density_p_ha"], 90)       # original untouched
        with self.assertRaises(EfeError):
            apply_overrides(self.cfg, ["no_equals_sign"])

    def test_missing_key_raises(self):
        with self.assertRaises(EfeError):
            core.get(self.cfg, "nope.x")


class TestSite(Base):
    def test_declination_and_h0(self):
        self.assertAlmostEqual(site.declination(172), 23.45, delta=0.2)
        self.assertTrue(10.3 < site.h0_daily(0, 80) < 10.7)

    def test_hemisphere_symmetry(self):
        c = core.load_json(core.DATA / "climates.json")["cape_town"]
        m = copy.deepcopy(c)
        m["lat"] = -c["lat"]
        m["ghi_kwh_m2_d"] = c["ghi_kwh_m2_d"][6:] + c["ghi_kwh_m2_d"][:6]
        a, b = sum(site.pv_specific_yield(c, 34)), sum(site.pv_specific_yield(m, 34))
        self.assertLess(abs(a - b) / a, 0.006)

    def test_optimum_tilt_reasonable(self):
        self.assertTrue(15 <= self.res["solar"]["opt_tilt"] <= 40)


class TestUrban(Base):
    def test_hex_area(self):
        self.assertAlmostEqual(urban.hex_metrics(300)["area_m2"], 2 * math.sqrt(3) * 300 ** 2, places=6)

    def test_points_inside(self):
        a = 300.0
        r = 2 * a / math.sqrt(3)
        for x, y in urban._sample_hex(a, 500, 1):
            self.assertLessEqual(math.sqrt(3) * abs(x) + abs(y), math.sqrt(3) * r + 1e-9)
            self.assertLessEqual(abs(y), a + 1e-9)

    def test_land_shares_sum(self):
        self.assertAlmostEqual(sum(self.res["land"]["shares_pct"].values()), 100.0, places=6)

    def test_ssd(self):
        self.assertAlmostEqual(urban.ssd_m(30, 2.5, 3.4), 2.5 * 30 / 3.6 + (30 / 3.6) ** 2 / 6.8, places=6)

    def test_tobler(self):
        self.assertAlmostEqual(urban.tobler_kmh(0.0), 6 * math.exp(-0.175), places=9)

    def test_access_beats_legacy(self):
        leg = urban.access_concentric(self.cfg["legacy"], 1.25, 4.8)
        hexa = self.res["access"]
        self.assertGreater(hexa["cell_node"]["cov"], leg["cell_node"]["cov"])
        self.assertLess(hexa["ward_node"]["p95_min"], leg["ward_node"]["p95_min"])

    def test_infeasible_density_raises(self):
        with self.assertRaises(EfeError):
            run_all(apply_overrides(self.cfg, ["geometry.gross_density_p_ha=400"]), only=["land"])


class TestResources(Base):
    def test_partitions_sum_to_one(self):
        for mode, d in self.cfg["water"]["partition"].items():
            for cls, p in d.items():
                self.assertAlmostEqual(p["evap"] + p["tank"] + p["infil"] + p["runoff"], 1.0, places=9, msg=f"{mode}/{cls}")

    def test_water_closure(self):
        self.assertLess(abs(self.res["water"]["closure_rel"]), 1e-9)

    def test_energy_closure(self):
        self.assertLess(abs(self.res["energy"]["closure_kwh_pp"]), 1e-6)

    def test_food_allocation_bounded(self):
        F = self.res["food"]
        for g, a in F["alloc_m2_pp"].items():
            self.assertLessEqual(a, F["need_m2_pp"][g] + 1e-9)
        self.assertLessEqual(F["kcal_ssr"], 1.0)

    def test_waste_composition_validated(self):
        c = apply_overrides(self.cfg, ["waste.composition.organics=0.9"])
        with self.assertRaises(EfeError):
            run_all(c, only=["waste"])

    def test_more_storage_never_hurts(self):
        lo = ev.evaluate(apply_overrides(self.cfg, ["energy.storage_kwh_pp=2"]))["k"]["energy_ssr"]
        hi = ev.evaluate(apply_overrides(self.cfg, ["energy.storage_kwh_pp=12"]))["k"]["energy_ssr"]
        self.assertGreaterEqual(hi, lo)


class TestResilience(Base):
    def test_wind_pressure(self):
        self.assertAlmostEqual(resilience.wind_q_kpa(40), 1.0, places=9)

    def test_seismic_plateau(self):
        self.assertAlmostEqual(resilience.seismic_cs(0.10, "C", 2.0), 0.14375, places=9)

    def test_street_flow_monotonic(self):
        d1 = resilience.street_flow(0.5, 30, 0.025, 0.02)[0]
        d2 = resilience.street_flow(1.0, 30, 0.025, 0.02)[0]
        self.assertGreater(d2, d1)

    def test_mca_excludes_unsafe(self):
        self.assertIn("overhead_bare", self.res["means"]["current"]["power"]["excluded"])
        self.assertIn("shared_trough", self.res["means"]["current"]["water"]["excluded"])

    def test_fmea_gate(self):
        self.assertTrue(self.res["fmea"]["gate"])

    def test_profiles_switch_system(self):
        p = self.res["structure"]["profiles"]
        self.assertEqual(p["stress_seismic"]["system"][0], "timber_bamboo_frame")
        self.assertTrue(p["stress_tornado"]["safe_rooms"])
        self.assertTrue(p["stress_cyclone"]["hurricane_envelope"])


class TestSynergy(Base):
    def test_matrix_symmetric(self):
        M = synergy.interaction_matrix("unified")
        for a in M["codes"]:
            for b in M["codes"]:
                if a != b:
                    self.assertEqual(M["cells"][(a, b)], M["cells"][(b, a)])

    def test_unified_saves_excavation(self):
        self.assertLess(synergy.UNIFIED["trough"][0] * synergy.UNIFIED["trough"][1] + synergy.UNIFIED["wet_strip"][0] * synergy.UNIFIED["wet_strip"][1],
                        sum(w * d for w, d, _ in synergy.TRENCH.values()))

    def test_conflicts_use_valid_codes(self):
        for a, b, _, _ in synergy.CONFLICTS:
            self.assertIn(a, synergy.SUBS)
            self.assertIn(b, synergy.SUBS)


class TestEvaluate(Base):
    def test_all_gates_pass(self):
        bad = [g["id"] for g in self.ev["gates"] if not g["ok"]]
        self.assertEqual(bad, [])

    def test_composite_range(self):
        self.assertTrue(0.0 <= self.ev["composite"] <= 1.0)

    def test_ladder_improves(self):
        lad = ev.iterations(self.cfg)
        self.assertGreater(lad[-1]["composite"], lad[0]["composite"] + 0.4)
        self.assertEqual(lad[-1]["gates_ok"], lad[-1]["gates_n"])

    def test_score_direction(self):
        k = dict(self.ev["k"])
        s1 = ev.scores(dict(k))
        k["potable_ssr"] = 0.2
        s2 = ev.scores(dict(k))
        self.assertLess(s2["potable_ssr"], s1["potable_ssr"])

    def test_global_sites_run(self):
        for cl in ("johannesburg", "durban", "lisbon", "nairobi"):
            c = apply_overrides(self.cfg, [f'site.climate="{cl}"', f'site.hazard_profile="{cl}"'])
            self.assertTrue(math.isfinite(ev.evaluate(c)["composite"]))


class TestReport(Base):
    def test_missing_placeholder_raises(self):
        with self.assertRaises(EfeError):
            report.render("{{nope.x}}", {})

    def test_directives(self):
        out = report.render("@P " + "word " * 60 + "\n{{a.b|.1f}}", {"a": {"b": 1.234}})
        self.assertTrue(all(len(x) <= report.W for x in out.splitlines()))
        self.assertIn("1.2", out)

    def test_build_width(self):
        an = analysis.run_analysis(self.cfg, quick=True)
        txt = report.build(self.cfg, an)
        self.assertLessEqual(max(len(x) for x in txt.splitlines()), report.W)
        self.assertNotIn("{{", txt)


if __name__ == "__main__":
    unittest.main()
