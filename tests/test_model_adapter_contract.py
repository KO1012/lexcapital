from finrulebench.adapters.mock_adapter import MockAdapter
from finrulebench.runners.run_config import RunConfig


def test_mock_adapter_returns_decision():
    adapter = MockAdapter('mock-hold')
    prompt = {'step': 0, 'visible_state': {'prices': {'X': {'mid': 1}}}}
    decision = adapter.decide(prompt, {}, RunConfig(model_name='mock-hold'))
    assert decision.step == 0
    assert decision.orders
