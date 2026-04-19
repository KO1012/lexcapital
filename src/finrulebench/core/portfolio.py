from __future__ import annotations

from copy import deepcopy

from finrulebench.core.models import ActionType, ExecutedTrade, PortfolioState, Position


class Portfolio:
    def __init__(self, starting_cash: float = 100.0):
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.positions: dict[str, Position] = {}
        self.peak_value = starting_cash
        self.turnover = 0.0
        self.invalid_action_count = 0
        self.last_prices: dict[str, dict] = {}

    def _mid_price(self, instrument_id: str, prices: dict) -> float:
        quote = prices.get(instrument_id, {})
        return float(quote.get('mid', quote.get('bid', quote.get('ask', 0.0))))

    def gross_exposure(self, prices: dict) -> float:
        exposure = 0.0
        for instrument_id, pos in self.positions.items():
            exposure += abs(pos.quantity) * self._mid_price(instrument_id, prices)
        return exposure

    def leverage(self, prices: dict) -> float:
        state = self.mark_to_market(0, prices)
        equity = max(state.portfolio_value, 1e-9)
        return self.gross_exposure(prices) / equity

    def apply_trade(self, trade: ExecutedTrade) -> None:
        signed_qty = trade.quantity
        if trade.action in {ActionType.SELL, ActionType.SHORT}:
            signed_qty = -abs(trade.quantity)
        elif trade.action in {ActionType.BUY, ActionType.COVER, ActionType.BUY_YES, ActionType.BUY_NO, ActionType.CONVERT}:
            signed_qty = abs(trade.quantity)
        self.cash -= signed_qty * trade.price
        self.cash -= trade.fee_usd + trade.slippage_usd
        self.cash += trade.rebate_usd
        self.turnover += trade.notional_usd / self.starting_cash
        position = self.positions.get(trade.instrument_id)
        if position is None:
            self.positions[trade.instrument_id] = Position(
                instrument_id=trade.instrument_id, quantity=signed_qty, avg_price=trade.price, opened_step=trade.step
            )
        else:
            new_qty = position.quantity + signed_qty
            if abs(new_qty) < 1e-9:
                self.positions.pop(trade.instrument_id, None)
            else:
                if position.quantity == 0 or (position.quantity > 0) == (signed_qty > 0):
                    weighted_cost = abs(position.quantity) * position.avg_price + abs(signed_qty) * trade.price
                    avg_price = weighted_cost / max(abs(new_qty), 1e-9)
                    opened_step = min(position.opened_step, trade.step)
                else:
                    avg_price = trade.price if abs(signed_qty) > abs(position.quantity) else position.avg_price
                    opened_step = trade.step if abs(signed_qty) > abs(position.quantity) else position.opened_step
                self.positions[trade.instrument_id] = Position(
                    instrument_id=trade.instrument_id, quantity=new_qty, avg_price=avg_price, opened_step=opened_step
                )

    def mark_to_market(self, step: int, prices: dict) -> PortfolioState:
        self.last_prices = deepcopy(prices)
        value = self.cash
        for instrument_id, pos in self.positions.items():
            value += pos.quantity * self._mid_price(instrument_id, prices)
        self.peak_value = max(self.peak_value, value)
        drawdown = 0.0 if self.peak_value <= 0 else max(0.0, (self.peak_value - value) / self.peak_value)
        return PortfolioState(
            step=step,
            cash=round(self.cash, 6),
            positions=deepcopy(self.positions),
            portfolio_value=round(value, 6),
            peak_value=round(self.peak_value, 6),
            max_drawdown=round(drawdown, 6),
            turnover=round(self.turnover, 6),
            gross_exposure=round(self.gross_exposure(prices), 6),
            invalid_action_count=self.invalid_action_count,
        )

    def state(self, step: int, prices: dict) -> PortfolioState:
        return self.mark_to_market(step, prices)
