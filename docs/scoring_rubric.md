# Scoring Rubric v0.2

LexCapital scores one scenario by combining simulated capital outcome, rule reasoning, risk management, calibration, and efficiency. A hard-DQ trap gates the scenario score to zero.

## Score dimensions

| Dimension | What it measures |
| --- | --- |
| Money score | Adjusted utility relative to cash baseline and oracle target. |
| Rule reasoning | Valid citations, coverage of key rules, and trap awareness. |
| Risk management | Drawdown, turnover, position limits, and declared risk limits. |
| Calibration | Confidence versus realized success. |
| Efficiency | Invalid actions and unnecessary extra decisions. |

## Trap classes

Prefer action-derived traps over metadata-only traps whenever possible:

- order notional versus liquidity,
- leverage and gross exposure,
- holding period and redemption gates,
- locate and closeout deadlines,
- collateral haircut and margin sufficiency,
- source hierarchy and timezone deadlines,
- no-context overtrading.

Metadata can support explanations, but the main scoring path should be determined from orders, timestamps, public rules, portfolio state, and visible market data.

## Audit signals

`audit-scenarios` reports:

- hidden leakage findings,
- HOLD non-DQ rate,
- oracle sidecar non-DQ rate,
- red sidecar trigger rate,
- difficulty/category/data-mode balance,
- trap-condition balance,
- expected-skill balance.

Use these signals to calibrate Phase-2 sets before running model comparisons.
