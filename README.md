# FinRuleBench

FinRuleBench is a sandboxed financial reasoning benchmark for AI models.

## Principles

- Every scenario starts with **100 USD**.
- All trading is simulated.
- Hidden fields never reach the evaluated model.
- Deterministic replay produces the final score.
- HOLD is always valid.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Minimal demo

```bash
python -m finrulebench validate scenarios/mvp
python -m finrulebench render-prompt --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml --step 0
python -m finrulebench run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold
python -m finrulebench score-dir runs/mock_hold
pytest -q
```

## What it evaluates

- financial rule reading
- legal-style compliance boundaries
- synthetic market traps
- risk control
- calibration under uncertainty

## Safety boundary

FinRuleBench does **not** connect to real broker APIs, exchanges, wallets, or live trading systems.

## Core commands

- `python -m finrulebench validate scenarios/mvp`
- `python -m finrulebench render-prompt --scenario ... --step 0`
- `python -m finrulebench make-hold-actions --scenario ... --out /tmp/hold.jsonl`
- `python -m finrulebench replay --scenario ... --actions ... --out runs/example`
- `python -m finrulebench run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold`
- `python -m finrulebench score-dir runs/mock_hold`
- `python -m finrulebench write-agent-template --out agent_eval.example.yaml`
- `python -m finrulebench agent-eval --config agent_eval.example.yaml`

## Agent integration

If you want to hand the repository to an external coding agent (for example Codex) and have it run evaluations for a configured model, use the agent-eval workflow.

1. Generate a config template:

```bash
python -m finrulebench write-agent-template --out agent_eval.yaml
```

2. Edit `agent_eval.yaml` and set:

- `adapter`: `openai`, `local-http`, `mock`, or `file`
- `model`: the target model name
- `mode`: `policy` or `agent`
- `scenarios`: scenario directory to run
- `out`: output directory for scores and logs

3. Run the evaluation:

```bash
python -m finrulebench agent-eval --config agent_eval.yaml
```

4. Read the result from:

```text
runs/.../suite_summary.json
runs/.../leaderboard_row.json
runs/.../<SCENARIO_ID>/score.json
```

This makes the repository agent-friendly: the agent only needs to edit a config file and run one command. The benchmark runner still enforces hidden-field isolation, deterministic replay, and simulated-only trading.

## Scoring

Adjusted utility uses final value, max drawdown, turnover, and invalid actions. Hard DQ sets scenario score to zero.

## Hidden-field defense

Prompt rendering uses an explicit allowlist. Hidden oracle text, trap conditions, hidden future data, and scoring config stay out of model prompts and run logs.

## Adding scenarios

Write YAML under `scenarios/mvp/` using the schema in `src/finrulebench/core/models.py`, then run:

```bash
python -m finrulebench validate scenarios/mvp
pytest -q
```
