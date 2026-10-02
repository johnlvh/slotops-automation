# slotops-automation

Rule-driven config validation & change-impact analysis for social slot game operations.

## TL;DR

Ops edit business rules in `studio/rules.md`. A build-time transpiler turns them into a deterministic Python validator. Runtime is pure Python — no LLM, no API calls.

Beyond `git diff`, the analyzer scores every field change by domain importance (`HIGH` / `MEDIUM` / `LOW`) so LiveOps can spot economic risks instantly.

Runs in two modes: **gate** (fails CI on violation) and **report** (dry-run for review).

> **Roadmap:** real LLM integration for code generation is planned for a later phase.

## Structure

```text
slotops-automation/
├── pipeline.py                 # entry point (logging + orchestration)
├── cli.py                      # ad-hoc: compare / validate-folder / validate-file
├── slotops.py                  # core: rules, generator, compare, batch
├── rule_catalog.py             # all rule code templates
├── configs/                    # v1 (baseline) / v2 (candidate)
└── studio/
    ├── rules.md                # source of truth (Ops-editable)
    ├── config_template.json    # schema
    ├── field_importance.json   # HIGH/MEDIUM/LOW map
    ├── templates/validator.py.template
    └── generated/validator.py  # auto-generated — do not edit
```

## Usage

```bash
python pipeline.py                 # report mode — always exit 0, full output diff + summary
python pipeline.py --strict        # gate mode — exit 1 if have 1 config ERROR (usefor CI)
```

Logs go to stdout and `logging.log`.

## CLI (ad-hoc tools)

For quick lookups without running the full pipeline. Requires the validator to be generated first (`python pipeline.py` once).

```bash
# Diff any two config files
python cli.py compare configs/v1/slot_zeus_002.json configs/v2/slot_zeus_002.json

# Batch-validate any folder
python cli.py validate-folder configs/v2

# Validate a single file
python cli.py validate-file configs/v2/slot_dragon_003.json
```

Exit codes: `0` pass · `1` violations · `2` file not found.

## Managing Rules

Rules live in **two places** that must stay in sync — `rules.md` (definition) and `rule_catalog.py` (code template). `validate_rules()` enforces this **bidirectionally**: a rule present on only one side aborts the pipeline. There is no silent drift.

### Add a rule

1. Append a block to `studio/rules.md`:

   ```markdown
   ## RULE-011
   field: payoutRate
   severity: ERROR
   condition: payoutRate must be between 0 and 1
   ```

2. Add a matching entry in `rule_catalog.py`:

   ```python
   "RULE-011": RuleDef(render=lambda **k: f'''def validate_{k['r_id']}(config):
       issues = []
       val = config.get("payoutRate")
       if val is not None and not (0 <= val <= 1):
           issues.append(ValidationIssue("{k['rule_id']}", "{k['field']}", "payoutRate must be in [0,1]", "{k['severity']}"))
       return issues'''),
   ```

3. Run `python pipeline.py`. Phase 2 validates the pair; Phase 1 generates the code.

### Edit a rule

- **Metadata only** (field / severity / condition text) → edit `rules.md`. Done.
- **Semantics** (change the actual logic) → edit **both** `rules.md` and the lambda in `rule_catalog.py`. A condition-hash guard is a planned safeguard.

### Delete a rule

Remove the `## RULE-XXX` block from `rules.md` **and** the entry from `rule_catalog.py`.
Leaving either side orphaned fails validation.

### Rename a rule ID

Treat as delete + add: update both sides atomically.

## Design Choices

- **`rules.md` is the source of truth** — Ops & QA work in Markdown, not code.
- **Catalog is separate** — code templates are reviewable independently of the generator.
- **Bidirectional sync enforced** — no rule can exist on only one side.
- **Build-time transpilation** — deterministic Python at runtime, zero LLM cost.
- **Impact-aware diff** — changes scored against a domain importance map.

## Assumptions

- Rule IDs follow `RULE-NNN` and are unique.
- Config schema is stable, described by `config_template.json`.
- All configs are JSON, UTF-8 encoded.

## Trade-offs

- **Fixed templates** — safe and reproducible; new rule shapes need new lambdas.
- **Mock LLM transpiler** — deterministic today, real API deferred.
- **Per-rule validation only** — no cross-rule conflict detection yet.
- **Condition drift** — semantic changes to a rule require manual catalog updates.

## AI Usage

- AI is used **only at build time** to translate natural-language conditions into
  Python blocks inside `templates/validator.py.template`.
- Runtime is 100% LLM-free — no hallucination reaches production.
- `validate_rules()` is the safety gate before any generated code is trusted.

## Roadmap

- **Real LLM integration** — OpenAI / Gemini / Anthropic with temperature=0 and structured outputs to translate `rules.md` on the fly.
- **Condition-hash guard** — detect when a rule's meaning changed in `rules.md` but the catalog wasn't updated.
- **Cross-rule conflict detection** — catch contradictory conditions at validation time.
- **Pre-deployment rule simulation** — dry-run a new rule across all configs before shipping.
- **Similar-config lookup** — given a config, surface the closest existing configs (schema/field-level similarity) to accelerate authoring and spot near-duplicates.
- **Realtime config report UI** — a dashboard rendering active configs visually (field heatmap, rule violations, diff timeline) for LiveOps at a glance.
- **Natural-language config mutator** — Ops describes intent; agent produces a field-level diff + risk score for human approval.

## License

[MIT](LICENSE)
