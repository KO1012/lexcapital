from finrulebench.core.prompt_renderer import render_model_prompt


def get_visible_state(scenario, step, portfolio_state):
    return render_model_prompt(scenario, step, portfolio_state)
