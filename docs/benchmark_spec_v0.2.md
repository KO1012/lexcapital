# LexCapital Benchmark Spec v0.2

LexCapital is a sandboxed financial decision benchmark. It evaluates whether a model can read visible financial rules, size simulated actions, avoid hidden or illegal bait, and produce decisions that replay deterministically.

## Scope

LexCapital scenarios are not financial advice, live trading, or broker/exchange integrations. Every scenario starts with 100 USD, all orders are simulated, and replay is deterministic.

## Scenario contract

Every scenario file must include:

- `id`, `category`, `title`, `difficulty`, `data_mode`, `starting_cash`, `max_steps`, and `question`.
- `instruments` and `allowed_actions`; `HOLD` must always be allowed.
- `timeline` with `visible` state for the model and optional `hidden_future` for the evaluator only.
- `public_rules` and optional `rule_packs`.
- `hidden_oracle_solution`, `trap_conditions`, and `scoring`.
- `provenance` for every non-synthetic scenario.

v0.2 adds optional benchmark metadata:

```yaml
expected_skill:
  - rule_reading
  - risk_sizing
  - compliance_boundary
trap_type: source_hierarchy_misread
baseline_expectations:
  hold_score_min: 70
  oracle_score_min: 85
  red_path_must_trigger:
    - SOURCE_HIERARCHY_MISREAD
```

## Tracks

Recommended Phase-2 tracks:

| Track | Purpose |
| --- | --- |
| `dev_public` | Public authoring and model-debug scenarios. |
| `eval_sealed` | Private leaderboard scenarios. |
| `real_public_snapshot` | Frozen public facts and prices; never live feeds. |
| `synthetic_law` | Deterministic compliance and rule traps. |
| `synthetic_market` | Market microstructure, collateral, queue, and source-hierarchy traps. |

## Authoring invariants

1. Hidden oracle text, hidden future data, trap conditions, scoring config, and author notes must never appear in prompts or run logs.
2. `HOLD` must be legal and replayable for every scenario.
3. A red path should trigger the intended trap when a sidecar file is supplied.
4. An oracle path should not hard-DQ when a sidecar file is supplied.
5. Real-data scenarios must include public source URLs and source notes.
6. The scoring spread should distinguish safe abstention, valid oracle behavior, and rule-breaking bait.

## Action sidecars

The audit tool discovers these sidecar names next to each scenario or in a sibling `actions/` directory:

- Oracle paths: `<scenario_stem>_oracle.jsonl`, `<scenario_stem>.oracle.jsonl`, `<scenario_id>_oracle.jsonl`.
- Red paths: `<scenario_stem>_red.jsonl`, `<scenario_stem>.red.jsonl`, `<scenario_id>_red.jsonl`.

Sidecars are optional for MVP validation but recommended for Phase-2 scenarios and required for sealed leaderboard calibration.
