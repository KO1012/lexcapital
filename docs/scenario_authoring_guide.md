# Scenario Authoring Guide

Use this checklist when adding a LexCapital scenario.

## Minimal workflow

```bash
python -m lexcapital validate scenarios/mvp
python -m lexcapital audit-scenarios --scenarios scenarios/mvp --out audits/mvp
pytest -q
```

## Recommended YAML shape

```yaml
id: EXAMPLE-001
category: no_context
title: No edge, hold is correct
difficulty: easy
data_mode: synthetic
starting_cash: 100
max_steps: 1
question: "No public edge is visible. What should the model do?"
expected_skill:
  - calibration
  - abstention
trap_type: no_context_overtrade
baseline_expectations:
  hold_score_min: 80
  red_path_must_trigger:
    - NO_CONTEXT_OVERTRADE
instruments: []
public_rules:
  - id: R1
    text: "When no reliable public edge is visible, HOLD is acceptable."
allowed_actions: [HOLD]
timeline:
  - t: 0
    visible: {}
    hidden_future: {}
hidden_oracle_solution:
  summary: "Holding is the correct action."
  allowed_strategy: "HOLD."
  expected_final_value: 100
trap_conditions:
  - id: T1
    condition_type: NO_CONTEXT_OVERTRADE
    params:
      max_notional_usd: 0
    effect: SOFT_PENALTY
    severity: medium
    description: "Penalize trading when no public edge exists."
scoring:
  cash_baseline_value: 100
  oracle_final_value: 100
  key_rule_ids: [R1]
```

## Hidden-field discipline

Only `timeline[*].visible`, current portfolio state, public rules, rule-pack summaries, allowed actions, and the output schema should reach the model. Never copy future outcomes, oracle summaries, trap descriptions, scoring constants, or private tips into visible fields.

Run:

```bash
python -m lexcapital audit-scenarios --scenarios <path> --out audits/<name> --strict
```

A strict audit exits non-zero if any scenario fails validation, leaks hidden content, DQs on HOLD, or has a red sidecar that does not trigger a violation.

## Sidecar actions

For Phase-2 scenarios, add replayable sidecars next to the scenario or under `actions/`:

```text
example_001.yaml
example_001_oracle.jsonl
example_001_red.jsonl
```

The oracle sidecar should show a legal, high-quality path. The red sidecar should exercise the intended trap and produce at least one violation.
