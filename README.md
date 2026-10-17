# AEQUMOD

AEQUCITY v2.0 - Synergetic EFE City blueprint and parametric model.

A city design in which roads, paving, signage, water, drainage, waterways,
electricity, internet, lighting, thermals, sound, agriculture, fauna, waste,
ablutions, public facilities, transport, bridges, machinery and maintenance
work as **one synergetic system**. It stays safe under quake, storm, flood,
fire and drought, and passes the Equidistributed Free Economy (EFE) filter
on every decision.

Every number in the blueprint is computed by the accompanying scripted model
(stdlib Python 3.12, unit-tested). Tables, schematics and the photo prompt
are generated from a single configuration file, so text, drawings and prompt
agree by construction.

## Headline specifications

- Cell (AEQUCELL): hexagon, apothem 300 m (600 m flat-to-flat), 31.2 ha,
  2,806 residents at 90 p/ha.
- Ward / City: 7 cells = 19,641 p; 7 wards = 137,490 p on 38.2 km2
  (R 3.5 km, incl. wedge + nature).
- Access: 97% within 400 m of a daily node (P95 4.9 min); ward services P95
  13.5 min.
- AEQUSPINE: seam 28 m / lane 12 m / path 6 m; 2 trenches (trough + wet
  strip) replace 6.
- Water: potable 100% self-supplied; irrigation 62%; drought 3 yr: unmet 3.2%.
- Energy: 3.86 kWp/p, 100% self-supply, export 3,317 kWh/p/yr, storage
  9.5 kWh/p.
- Food: fresh produce 100% in-city + ward belt; 13% of kcal.

## Repository layout

```
AEQUCITY_v2.0_BLUEPRINT.md   full blueprint (ODF v1.0, SI units)
S-01_ward_plan.svg            ward plan schematic
S-02_corridor_sections.svg    corridor section schematic
S-03_cell_metabolism.svg      cell metabolism schematic
efe_city_model/               parametric model (Python 3.12, stdlib only)
  README.md                   model usage and layout
  AGENT_GUIDE.md              rules for editing the model
  efe_city/                   subsystems, evaluation, analysis, drawings, ...
  configs/                    JSON configs (iterations, reference site)
  data/                       climate and hazard JSON
  templates/                  ODF templates with {{path|fmt}} placeholders
  tests/                      37 unit tests
  out/                        generated artefacts (regenerate, do not commit)
```

## Running the model

```bash
cd efe_city_model
python -m efe_city check                            # exit 1 if any gate fails (CI)
python -m efe_city run                              # KPIs + gates
python -m efe_city analyze --out out                # ladder, plateau, sweeps, stress
python -m efe_city draw    --out out/schematics     # S-01/S-02/S-03
python -m efe_city build   --out out                # blueprint (.odf.txt + .md)
python -m unittest discover -s tests                # 37 tests
```

Examples: `--set geometry.gross_density_p_ha=80`,
`--set site.climate="lisbon" --set site.hazard_profile="lisbon"`.

## Status

DESIGN-BASIS PLATEAU (model-verified), 10 field gates open. Climate, hazard and
cost inputs are indicative; replace with site data (see blueprint sections
13.6-13.7). Planning-grade only - not certified construction documents.

## Licensing

Intended licence: CC-BY-SA (EFE open policy). Add a LICENSE file per your
repository policy before redistribution.

## Provenance

Extracted from `files.zip` (AEQUCITY v2.0 bundle) into this repository.
Agent: EFE OPTIBEST ENGINEER v2.0 (ODF v1.0, SI units).
Supersedes: AequCity v1.0 framework (ttx89-dev/resources/aequcity.md).
EOF
