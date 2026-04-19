TOOL_REGISTRY = ["get_visible_state", "get_portfolio_state", "calculate", "submit_decision"]

TOOL_POLICY = {
    "allowed_tools": TOOL_REGISTRY,
    "max_tool_calls_per_step": 5,
    "max_submit_decision_calls_per_step": 1,
    "filesystem_access": False,
    "shell_access": False,
    "web_access": False,
    "real_trading_access": False,
    "hidden_scenario_access": False,
}
