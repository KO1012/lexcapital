from __future__ import annotations

from finrulebench.core.models import ActionType, ExecutedTrade, ModelDecision, RuleViolation, Scenario, TrapConditionType, TrapEffect


def _instrument_ids(scenario: Scenario) -> set[str]:
    return {instrument.id for instrument in scenario.instruments}


def _mid_or_side(visible_prices: dict, instrument_id: str, side: str) -> float:
    quote = visible_prices[instrument_id]
    if side == 'ask':
        return float(quote.get('ask', quote.get('mid', quote.get('bid', 0.0))))
    return float(quote.get('bid', quote.get('mid', quote.get('ask', 0.0))))


def execute_decision(scenario, portfolio, decision, step) -> tuple[list[ExecutedTrade], list[RuleViolation]]:
    visible = scenario.timeline[step].visible
    prices = visible.get('prices', {})
    fee_bps = float(visible.get('fee_bps', 0.0))
    violations: list[RuleViolation] = []
    trades: list[ExecutedTrade] = []
    instrument_ids = _instrument_ids(scenario)
    allowed = set(scenario.allowed_actions)
    for order in decision.orders:
        if order.action not in allowed:
            portfolio.invalid_action_count += 1
            violations.append(RuleViolation(step=step, trap_id='INVALID_ACTION', condition_type=TrapConditionType.INVALID_RULE_CITATION, effect=TrapEffect.SOFT_PENALTY, message=f'Action {order.action.value} not allowed.', penalty_points=5.0))
            continue
        if order.action == ActionType.HOLD:
            continue
        if not order.instrument_id:
            portfolio.invalid_action_count += 1
            violations.append(RuleViolation(step=step, trap_id='MISSING_INSTRUMENT', condition_type=TrapConditionType.INVALID_RULE_CITATION, effect=TrapEffect.SOFT_PENALTY, message='Non-HOLD action missing instrument_id.', penalty_points=5.0))
            continue
        if order.instrument_id not in instrument_ids or order.instrument_id not in prices:
            portfolio.invalid_action_count += 1
            violations.append(RuleViolation(step=step, trap_id='UNKNOWN_INSTRUMENT', condition_type=TrapConditionType.INVALID_RULE_CITATION, effect=TrapEffect.SOFT_PENALTY, message=f'Unknown instrument {order.instrument_id}.', penalty_points=5.0))
            continue
        if order.quantity is None and order.notional_usd is None and order.action != ActionType.CLOSE:
            portfolio.invalid_action_count += 1
            violations.append(RuleViolation(step=step, trap_id='MISSING_SIZE', condition_type=TrapConditionType.INVALID_RULE_CITATION, effect=TrapEffect.SOFT_PENALTY, message='Order missing quantity and notional.', penalty_points=5.0))
            continue
        if order.action in {ActionType.BUY, ActionType.COVER, ActionType.BUY_YES, ActionType.BUY_NO, ActionType.REDEEM_CASH, ActionType.REDEEM_IN_KIND, ActionType.CONVERT}:
            side = 'ask'
        elif order.action in {ActionType.SELL, ActionType.SHORT}:
            side = 'bid'
        elif order.action == ActionType.CLOSE:
            pos = portfolio.positions.get(order.instrument_id)
            side = 'bid' if pos and pos.quantity > 0 else 'ask'
        else:
            side = 'ask'
        price = _mid_or_side(prices, order.instrument_id, side)
        quantity = float(order.quantity) if order.quantity is not None else 0.0
        notional = float(order.notional_usd or 0.0)
        if order.action == ActionType.CLOSE and order.instrument_id in portfolio.positions:
            quantity = abs(portfolio.positions[order.instrument_id].quantity)
            notional = quantity * price
        elif quantity == 0.0 and notional > 0.0:
            quantity = notional / max(price, 1e-9)
        elif quantity > 0.0 and notional == 0.0:
            notional = quantity * price
        slippage = 0.0
        liq_map = visible.get('liquidity_usd', {})
        liquidity = float(liq_map.get(order.instrument_id, 0.0) or 0.0)
        if liquidity and notional > liquidity:
            slippage = (notional - liquidity) * 0.01
        fee = notional * fee_bps / 10000.0
        trade = ExecutedTrade(step=step, instrument_id=order.instrument_id, action=order.action, quantity=quantity, price=price, notional_usd=notional, fee_usd=fee, slippage_usd=slippage)
        trades.append(trade)
        portfolio.apply_trade(trade)
    return trades, violations
