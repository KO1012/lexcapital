from __future__ import annotations

import csv
import json
from pathlib import Path


def build_leaderboard(path: str) -> dict:
    run_root = Path(path)
    rows = []
    for score_path in sorted(run_root.glob('**/score.json')):
        score = json.loads(score_path.read_text(encoding='utf-8'))
        rows.append(score)
    scenario_count = len(rows)
    overall = sum(r['scenario_score'] for r in rows) / scenario_count if scenario_count else 0.0
    non_dq = [r for r in rows if r['gate'] == 1]
    avg_final = sum(r['final_value'] for r in non_dq) / len(non_dq) if non_dq else 0.0
    dq_count = sum(1 for r in rows if r['gate'] == 0)
    summary = {
        'model_name': run_root.name,
        'provider': 'mock',
        'mode': 'policy',
        'overall_score': round(overall, 6),
        'capital_score': round(avg_final, 6),
        'compliance_score': round(max(0.0, 100 - dq_count * 10), 6),
        'robustness_score': 100.0,
        'dq_count': dq_count,
        'avg_final_value': round(avg_final, 6),
        'avg_max_drawdown': 0.0,
        'avg_turnover': 0.0,
        'scenario_count': scenario_count,
    }
    (run_root / 'leaderboard.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    with (run_root / 'leaderboard.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    return summary
