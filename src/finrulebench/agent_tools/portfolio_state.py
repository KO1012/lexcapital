from __future__ import annotations


def get_portfolio_state(portfolio_state):
    """Return only the public portfolio state already visible to the evaluated model."""
    if hasattr(portfolio_state, "model_dump"):
        return portfolio_state.model_dump()
    return dict(portfolio_state)
