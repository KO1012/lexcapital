from __future__ import annotations

import json
from pathlib import Path

from lexcapital.adapters.local_http import LocalHTTPAdapter
from lexcapital.adapters.openai_responses import OpenAIResponsesAdapter
from lexcapital.core.replay import replay_scenario
from lexcapital.runners.agent_runner import run_and_replay_agent_scenario
from lexcapital.runners.run_config import RunConfig
from lexcapital.runners.suite_runner import iter_scenario_paths


def _decision(step=0):
    return {
        "step": step,
        "orders": [{"action": "HOLD"}],
        "rule_citations": [],
        "risk_limit": None,
        "confidence": 0.5,
        "rationale_summary": "Hold.",
        "evidence_timestamps": [step],
        "metadata": {},
    }


class FakeResponses:
    def create(self, **kwargs):
        class Resp:
            output_text = json.dumps(_decision(0))
            usage = {"input_tokens": 1, "output_tokens": 1}
        return Resp()


class FakeOpenAIClient:
    responses = FakeResponses()


def test_openai_adapter_with_injected_client_parses_decision():
    adapter = OpenAIResponsesAdapter(client=FakeOpenAIClient())
    prompt = {"step": 0, "visible_state": {}, "required_output_schema": {}}
    decision = adapter.decide(prompt, {}, RunConfig(model_name="fake", provider="openai"))
    assert decision.orders[0].action.value == "HOLD"
    assert decision.metadata["provider"] == "openai"


class FakeLocalHTTPAdapter(LocalHTTPAdapter):
    def _post_json(self, url, payload, timeout):
        return {"choices": [{"message": {"content": json.dumps(_decision(0))}}], "usage": {}}


def test_local_http_adapter_parses_openai_compatible_response():
    adapter = FakeLocalHTTPAdapter("http://localhost:8000")
    prompt = {"step": 0, "visible_state": {}, "required_output_schema": {}}
    decision = adapter.decide(prompt, {}, RunConfig(model_name="fake", provider="local_http"))
    assert decision.orders[0].action.value == "HOLD"
    assert decision.metadata["provider"] == "local_http"


def test_iter_scenario_paths_recurses(tmp_path: Path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "a.yaml").write_text("id: A\n", encoding="utf-8")
    (tmp_path / "rule_packs").mkdir()
    (tmp_path / "rule_packs" / "skip.yaml").write_text("id: SKIP\n", encoding="utf-8")
    paths = list(iter_scenario_paths(tmp_path))
    assert paths == [tmp_path / "nested" / "a.yaml"]


def test_replay_invalid_json_defaults_to_hold(tmp_path: Path):
    scenario = Path("scenarios/mvp/noctx_001_no_edge_hold.yaml")
    if not scenario.exists():
        return
    actions = tmp_path / "bad_actions.jsonl"
    actions.write_text("not-json\n", encoding="utf-8")
    out = tmp_path / "run"
    result = replay_scenario(str(scenario), str(actions), str(out))
    assert result.final_value >= 0
    violations = (out / "rule_violations.jsonl").read_text(encoding="utf-8")
    assert "INVALID_MODEL_OUTPUT" in violations


class CanaryCheckingAdapter:
    name = "canary-check"
    provider = "mock"

    def decide(self, prompt, decision_schema, run_config):
        rendered = json.dumps(prompt, ensure_ascii=False)
        assert "hidden_oracle_solution" not in rendered
        assert "trap_conditions" not in rendered
        assert "hidden_future" not in rendered
        return _decision(prompt["step"])


def test_agent_mode_does_not_expose_hidden_fields(tmp_path: Path):
    scenario = Path("scenarios/mvp/noctx_001_no_edge_hold.yaml")
    if not scenario.exists():
        return
    out = tmp_path / "agent"
    run_and_replay_agent_scenario(
        scenario,
        CanaryCheckingAdapter(),
        RunConfig(model_name="canary", provider="mock", mode="agent"),
        out,
    )
    rendered = (out / "rendered_prompts.jsonl").read_text(encoding="utf-8")
    assert "hidden_oracle_solution" not in rendered
    assert "trap_conditions" not in rendered
