# FinRuleBench Agent Instructions

## Project purpose

FinRuleBench is a sandboxed AI financial decision benchmark. It evaluates models on simulated trading scenarios with legal-style rules, hidden traps, risk constraints, and deterministic scoring.

## Non-negotiable safety rules

- Never connect to real brokerages, real exchanges, wallets, or live trading APIs.
- Never implement real-world market manipulation, wash trading, spoofing, illegal arbitrage, or regulatory evasion.
- All trading must be simulated.
- Rule loopholes are synthetic scenario mechanics only.
- Never expose hidden_oracle_solution, trap_conditions, hidden_future, scoring, or notes_for_authors to model prompts.
- Do not require or reveal chain-of-thought. Use short rationale summaries only.
- Do not use Python eval or exec on scenario YAML fields.

## Engineering rules

- Use Python 3.11+.
- Use pydantic v2 for schemas.
- Every scenario must have deterministic validation, replay, and scoring.
- Every scenario starts with 100 USD.
- HOLD must be a valid action.
- Replay is deterministic and based on saved actions.jsonl.
- The model runner collects actions; the replay engine scores them.
- Private hidden fields must never be sent to adapters or agents.

## Required verification commands

```bash
python -m finrulebench validate scenarios/mvp
python -m finrulebench render-prompt --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml --step 0
python -m finrulebench make-hold-actions --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml --out /tmp/noctx_hold.jsonl
python -m finrulebench replay --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml --actions /tmp/noctx_hold.jsonl --out runs/noctx_hold
python -m finrulebench run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold
pytest -q
```

## Definition of done

A change is done only when:

- all relevant tests pass
- CLI commands run successfully
- hidden fields are not leaked
- no real trading integration exists
- README explains the new behavior
