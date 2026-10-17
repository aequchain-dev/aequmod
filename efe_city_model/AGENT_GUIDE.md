# Agent guide
1. Always run `python -m efe_city check` before and after edits; all 18 gates must pass unless the task changes a gate.
2. Never hard-code numbers in templates; use `{{dotted.path|fmt}}` or a `@table_fn`. Missing keys raise by design.
3. Keep subsystems pure: `fn(cfg, res) -> dict`; declare `needs`; no globals except constants.
4. Any new physical balance must expose a `closure` value and get a test.
5. Never model an energy source other than sun, wind, biomass or grid partnership; converters have eta < 1.
6. Mark unverified inputs as indicative in `content.LIMITS`; do not claim certification beyond DESIGN-BASIS.
7. Regenerate everything with `analyze` then `build`; commit config + templates, not `out/`.
