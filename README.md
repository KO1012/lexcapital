# lexcapital

**English** | [中文](#中文介绍)

lexcapital is a sandboxed financial reasoning benchmark for AI models. It tests whether an AI system can read financial and legal-style rules, avoid hidden traps, manage risk, and produce deterministic decisions under uncertainty — without touching real markets.

> Safety first: lexcapital is simulation-only. It never connects to real broker APIs, exchanges, wallets, or live trading systems.

## Why lexcapital exists

Modern AI models are increasingly asked to reason about capital allocation, compliance constraints, and uncertain market-like environments. Simple Q&A benchmarks do not reveal whether a model can follow rules across multiple steps, avoid tempting but invalid actions, or preserve downside protection when the prompt is adversarial.

lexcapital turns those questions into reproducible benchmark scenarios. Each scenario starts with **100 USD**, exposes only the information a model is allowed to see, records the model's actions, and then replays them through deterministic scoring.

## What it evaluates

- Financial rule reading and instruction following
- Legal-style compliance boundaries
- Synthetic market traps and loophole resistance
- Risk control, drawdown awareness, and turnover discipline
- Calibration under uncertainty
- Hidden-field leakage resistance

## Core principles

- Every scenario starts with **100 USD**.
- All trading is simulated.
- Hidden fields never reach the evaluated model.
- Deterministic replay produces the final score.
- `HOLD` is always a valid action.
- The benchmark must never require or reveal chain-of-thought; short rationale summaries are enough.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Minimal demo

```bash
python -m lexcapital validate scenarios/mvp
python -m lexcapital render-prompt --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml --step 0
python -m lexcapital run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold
python -m lexcapital run-baseline --policy rule-aware --scenarios scenarios/mvp --out runs/baselines/rule_aware
python -m lexcapital run-baseline --policy risk-aware --scenarios scenarios/mvp --out runs/baselines/risk_aware
python -m lexcapital run-baseline --policy oracle-lite --scenarios scenarios/mvp --out runs/baselines/oracle_lite
python -m lexcapital publish-check --scenarios scenarios/mvp --out audits/publish_mvp
python -m lexcapital score-dir runs/mock_hold
pytest -q
```

## Core commands

- `python -m lexcapital validate scenarios/mvp`
- `python -m lexcapital render-prompt --scenario ... --step 0`
- `python -m lexcapital render-next --scenario ... --actions ...`
- `python -m lexcapital make-hold-actions --scenario ... --out /tmp/hold.jsonl`
- `python -m lexcapital replay --scenario ... --actions ... --out runs/example`
- `python -m lexcapital run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold`
- `python -m lexcapital run-baseline --policy hold --scenarios scenarios/mvp --out runs/baselines/hold`
- `python -m lexcapital run-baseline --policy random-valid --seed 42 --scenarios scenarios/mvp --out runs/baselines/random_valid`
- `python -m lexcapital run-baseline --policy rule-aware --scenarios scenarios/mvp --out runs/baselines/rule_aware`
- `python -m lexcapital run-baseline --policy risk-aware --scenarios scenarios/mvp --out runs/baselines/risk_aware`
- `python -m lexcapital run-baseline --policy oracle-lite --scenarios scenarios/mvp --out runs/baselines/oracle_lite`
- `python -m lexcapital publish-check --scenarios scenarios/mvp --out audits/publish_mvp`
- `python -m lexcapital score-dir runs/mock_hold`
- `python -m lexcapital write-agent-template --out agent_eval.example.yaml`
- `python -m lexcapital agent-eval --config agent_eval.example.yaml`
- `python -m lexcapital self-eval`
- `python -m lexcapital audit-scenarios --scenarios scenarios/mvp --out audits/mvp`

## Agent integration

There are two supported workflows for external coding agents.

### 1) API-backed model evaluation

Use this when the repository should call a configured provider adapter such as OpenAI or a local OpenAI-compatible endpoint.

```bash
python -m lexcapital self-eval \
  --adapter openai \
  --model gpt-5.4 \
  --scenarios scenarios/mvp \
  --out runs/gpt_5_4_self_eval
```

If your environment already exports `LEXCAPITAL_AGENT_ADAPTER` and `LEXCAPITAL_AGENT_MODEL`, the coding agent can often just run:

```bash
python -m lexcapital self-eval
```

### 2) Current coding agent self-evaluation

Use this when the external coding agent itself is the model being tested and the repository should **not** call a provider API.

The loop is:

1. Create an empty actions file for a scenario.
2. Ask for the next visible prompt:

```bash
python -m lexcapital render-next \
  --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml \
  --actions runs/self_eval/NOCTX-001/actions.jsonl
```

3. Append exactly one `ModelDecision` JSON line for the returned `next_step` using the agent's own reasoning.
4. Repeat `render-next` until it returns `{"done": true, ...}`.
5. Score the scenario:

```bash
python -m lexcapital replay \
  --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml \
  --actions runs/self_eval/NOCTX-001/actions.jsonl \
  --out runs/self_eval/NOCTX-001
```

6. Aggregate all scenario scores with:

```bash
python -m lexcapital score-dir runs/self_eval
```

This makes the repository usable even when the coding agent cannot expose its current model/provider to the benchmark code directly.

## Scoring

Adjusted utility uses final value, max drawdown, turnover, and invalid actions. Hard DQ sets scenario score to zero.

## Hidden-field defense

Prompt rendering uses an explicit allowlist. Hidden oracle text, trap conditions, hidden future data, and scoring config stay out of model prompts and run logs.

## Adding scenarios

Write YAML under `scenarios/mvp/` using the schema in `src/lexcapital/core/models.py`, then run:

```bash
python -m lexcapital validate scenarios/mvp
pytest -q
```

## v0.4 leaderboard protocol

v0.4 writes leaderboard-ready artifacts for every suite or baseline run:

- `results.json`: full machine-readable run output with per-scenario scores
- `model_card.json`: provider/model/config/access boundary metadata
- `leaderboard_row.json`: one normalized leaderboard submission row
- `leaderboard.csv`: flat CSV row for aggregation

The public baselines are `hold`, `random-valid`, `rule-aware`, `risk-aware`, and `oracle-lite`.

## v0.3 scenario audit and publish gate

Use the audit and publish-check commands before expanding the benchmark or publishing a run:

```bash
python -m lexcapital audit-scenarios --scenarios scenarios/mvp --out audits/mvp_v0.3 --strict
python -m lexcapital publish-check --scenarios scenarios/mvp --out audits/publish_mvp_v0.3
```

The audit checks hidden-field leakage, HOLD replay safety, oracle/red sidecars, metadata coverage, provenance coverage, and category/difficulty/trap balance. It writes `audit_report.json` and `audit_summary.md`; publish-check writes `publish_report.json` and `publish_summary.md`.

## v0.4 docs

- `docs/benchmark_spec_v0.4.md`
- `docs/leaderboard_schema_v0.4.md`
- `docs/v0.4_release_notes.md`
- `docs/scenario_authoring_guide.md`
- `docs/eval_protocol.md`
- `docs/scoring_rubric.md`

---

# 中文介绍

[English](#lexcapital) | **中文**

lexcapital 是一个面向 AI 模型的**沙盒金融推理基准**。它用完全模拟的交易场景，测试模型能否读懂金融规则和类法律约束、避开隐藏陷阱、控制风险，并在不确定环境下给出可复现的决策。

> 安全边界：lexcapital 只做模拟评测，不连接任何真实券商 API、交易所、钱包或实时交易系统。

## 为什么做 lexcapital

AI 模型正在越来越多地参与资本配置、合规判断和市场推理类任务。普通问答基准很难看出一个模型是否真的能在多步决策里遵守规则、拒绝诱人的违规动作，或者在对抗性提示中保持风险纪律。

lexcapital 把这些能力拆成可复现的 benchmark 场景。每个场景都从 **100 USD** 开始，只向模型展示允许公开的信息，记录模型动作，再通过确定性的 replay 和 scoring 产出最终成绩。

## 评测能力

- 金融规则阅读与指令遵循
- 类法律/合规边界判断
- 合成市场陷阱与漏洞诱导抵抗
- 风险控制、回撤意识和换手纪律
- 不确定性下的校准能力
- 隐藏字段泄漏防护

## 核心原则

- 每个场景初始资金都是 **100 USD**。
- 所有交易都只是模拟。
- 隐藏字段不会进入被测模型的 prompt。
- 最终分数由确定性的 replay 生成。
- `HOLD` 永远是合法动作。
- 不要求也不暴露 chain-of-thought；简短理由摘要即可。

## 安装

```bash
python -m pip install -e ".[dev]"
```

## 最小演示

```bash
python -m lexcapital validate scenarios/mvp
python -m lexcapital render-prompt --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml --step 0
python -m lexcapital run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold
python -m lexcapital run-baseline --policy rule-aware --scenarios scenarios/mvp --out runs/baselines/rule_aware
python -m lexcapital run-baseline --policy risk-aware --scenarios scenarios/mvp --out runs/baselines/risk_aware
python -m lexcapital run-baseline --policy oracle-lite --scenarios scenarios/mvp --out runs/baselines/oracle_lite
python -m lexcapital publish-check --scenarios scenarios/mvp --out audits/publish_mvp
python -m lexcapital score-dir runs/mock_hold
pytest -q
```

## 常用命令

- `python -m lexcapital validate scenarios/mvp`
- `python -m lexcapital render-prompt --scenario ... --step 0`
- `python -m lexcapital render-next --scenario ... --actions ...`
- `python -m lexcapital make-hold-actions --scenario ... --out /tmp/hold.jsonl`
- `python -m lexcapital replay --scenario ... --actions ... --out runs/example`
- `python -m lexcapital run-suite --scenarios scenarios/mvp --adapter mock --model mock-hold --out runs/mock_hold`
- `python -m lexcapital run-baseline --policy hold --scenarios scenarios/mvp --out runs/baselines/hold`
- `python -m lexcapital run-baseline --policy random-valid --seed 42 --scenarios scenarios/mvp --out runs/baselines/random_valid`
- `python -m lexcapital run-baseline --policy rule-aware --scenarios scenarios/mvp --out runs/baselines/rule_aware`
- `python -m lexcapital run-baseline --policy risk-aware --scenarios scenarios/mvp --out runs/baselines/risk_aware`
- `python -m lexcapital run-baseline --policy oracle-lite --scenarios scenarios/mvp --out runs/baselines/oracle_lite`
- `python -m lexcapital publish-check --scenarios scenarios/mvp --out audits/publish_mvp`
- `python -m lexcapital score-dir runs/mock_hold`
- `python -m lexcapital write-agent-template --out agent_eval.example.yaml`
- `python -m lexcapital agent-eval --config agent_eval.example.yaml`
- `python -m lexcapital self-eval`
- `python -m lexcapital audit-scenarios --scenarios scenarios/mvp --out audits/mvp`

## Agent 接入方式

外部 coding agent 有两种接入方式。

### 1）通过 API 调用模型评测

适用于仓库可以调用 OpenAI 等 provider adapter，或本地 OpenAI-compatible endpoint 的情况。

```bash
python -m lexcapital self-eval \
  --adapter openai \
  --model gpt-5.4 \
  --scenarios scenarios/mvp \
  --out runs/gpt_5_4_self_eval
```

如果环境已经导出 `LEXCAPITAL_AGENT_ADAPTER` 和 `LEXCAPITAL_AGENT_MODEL`，coding agent 通常可以直接运行：

```bash
python -m lexcapital self-eval
```

### 2）当前 coding agent 自评测

适用于外部 coding agent 本身就是被测模型，并且仓库不应直接调用 provider API 的情况。

流程如下：

1. 为某个 scenario 创建空的 actions 文件。
2. 获取下一步可见 prompt：

```bash
python -m lexcapital render-next \
  --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml \
  --actions runs/self_eval/NOCTX-001/actions.jsonl
```

3. 针对返回的 `next_step` 追加一行 `ModelDecision` JSON。
4. 重复 `render-next`，直到返回 `{"done": true, ...}`。
5. 对该 scenario 进行 replay 评分：

```bash
python -m lexcapital replay \
  --scenario scenarios/mvp/noctx_001_no_edge_hold.yaml \
  --actions runs/self_eval/NOCTX-001/actions.jsonl \
  --out runs/self_eval/NOCTX-001
```

6. 汇总全部 scenario 分数：

```bash
python -m lexcapital score-dir runs/self_eval
```

这种方式让仓库在无法直接知道当前 agent 模型/provider 的情况下，也能完成评测。

## 评分方式

Adjusted utility 综合最终资产、最大回撤、换手率和无效动作。触发 hard DQ 的场景分数为零。

## 隐藏字段防护

Prompt 渲染使用显式 allowlist。隐藏 oracle 文本、trap conditions、hidden future data 和 scoring config 都不会进入模型 prompt 或运行日志。

## 添加场景

在 `scenarios/mvp/` 下编写符合 `src/lexcapital/core/models.py` schema 的 YAML，然后运行：

```bash
python -m lexcapital validate scenarios/mvp
pytest -q
```

## v0.4 leaderboard 协议

v0.4 会为每次 suite 或 baseline run 生成 leaderboard-ready artifacts：

- `results.json`：完整机器可读结果，包含每个 scenario 的分数
- `model_card.json`：provider/model/config/access boundary 元数据
- `leaderboard_row.json`：标准化 leaderboard 提交行
- `leaderboard.csv`：便于聚合的 CSV 行

公开 baselines 包括 `hold`、`random-valid`、`rule-aware`、`risk-aware` 和 `oracle-lite`。

## v0.3 scenario audit 和发布门禁

扩展 benchmark 或发布 run 前，建议运行 audit 与 publish-check：

```bash
python -m lexcapital audit-scenarios --scenarios scenarios/mvp --out audits/mvp_v0.3 --strict
python -m lexcapital publish-check --scenarios scenarios/mvp --out audits/publish_mvp_v0.3
```

Audit 会检查隐藏字段泄漏、HOLD replay 安全性、oracle/red sidecars、metadata 覆盖、provenance 覆盖，以及类别/难度/trap 平衡。它会写出 `audit_report.json` 和 `audit_summary.md`；publish-check 会写出 `publish_report.json` 和 `publish_summary.md`。

## v0.4 文档

- `docs/benchmark_spec_v0.4.md`
- `docs/leaderboard_schema_v0.4.md`
- `docs/v0.4_release_notes.md`
- `docs/scenario_authoring_guide.md`
- `docs/eval_protocol.md`
- `docs/scoring_rubric.md`
