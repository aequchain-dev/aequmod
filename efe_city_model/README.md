# efe_city - parametric EFE city model (AEQUCITY v2.0)

Stdlib-only Python 3.12. One JSON config drives geometry, water, energy, food, waste, hazards, economics,
KPIs/gates, schematics (SVG) and the ODF blueprint, so numbers, drawings and the photo prompt always agree.

    python -m efe_city run     [--config F] [--set key=json ...]    # KPIs + gates
    python -m efe_city check                                         # exit 1 if any gate fails (CI)
    python -m efe_city analyze --out out                             # ladder, plateau search, sweeps, stress, site adapter
    python -m efe_city draw    --out out/schematics                  # S-01 ward plan, S-02 sections, S-03 metabolism
    python -m efe_city build   --out out                             # blueprint (.odf.txt + fenced .md)
    python -m unittest discover -s tests                             # 37 tests

Examples: `--set geometry.gross_density_p_ha=80`, `--set site.climate="lisbon" --set site.hazard_profile="lisbon"`.

Layout: `efe_city/{core,site,urban,resources,resilience,synergy,economics,evaluate,analysis,drawings,report,tables,content,cli}.py`,
`configs/*.json`, `data/{climates,hazards}.json`, `templates/*.odf` (text + `{{path|fmt}}` / `{{table:name}}` placeholders).

Extend: add a subsystem with `@subsystem(name, needs=(...))`; a KPI in `evaluate.SPEC`; a table with `@table_fn`;
a site by adding climate + hazard JSON; a design iteration in `configs/iterations.json`.

Status: planning-grade. Climate, hazard and cost inputs are indicative; replace with site data (see blueprint 13.6-13.7).
Intended licence: CC-BY-SA (EFE open policy) - add a LICENSE file per your repository policy.
