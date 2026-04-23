from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ScenarioCategory(str, Enum):
    rule_arbitrage = "rule_arbitrage"
    stocks = "stocks"
    funds_etfs = "funds_etfs"
    crypto = "crypto"
    prediction_markets = "prediction_markets"
    no_context = "no_context"
    macro = "macro"
    rates = "rates"
    legal_rules = "legal_rules"
    regulation = "regulation"
    options = "options"


class DataMode(str, Enum):
    synthetic = "synthetic"
    frozen_real_snapshot = "frozen_real_snapshot"
    real_rule_plus_synthetic_prices = "real_rule_plus_synthetic_prices"
    real_public_snapshot = "real_public_snapshot"
    real_fact_plus_synthetic_prices = "real_fact_plus_synthetic_prices"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"
    expert = "expert"


class ActionType(str, Enum):
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    REDEEM_CASH = "REDEEM_CASH"
    REDEEM_IN_KIND = "REDEEM_IN_KIND"
    CONVERT = "CONVERT"
    TRANSFER = "TRANSFER"
    CLOSE = "CLOSE"


class TrapEffect(str, Enum):
    HARD_DQ = "HARD_DQ"
    SOFT_PENALTY = "SOFT_PENALTY"
    APPLY_SLIPPAGE = "APPLY_SLIPPAGE"
    REMOVE_REBATE = "REMOVE_REBATE"
    APPLY_FEE = "APPLY_FEE"
    CAP_PROFIT = "CAP_PROFIT"
    FORCE_QUEUE_DELAY = "FORCE_QUEUE_DELAY"
    MARGIN_CALL = "MARGIN_CALL"


class TrapConditionType(str, Enum):
    FUTURE_DATA_USED = "FUTURE_DATA_USED"
    INVALID_RULE_CITATION = "INVALID_RULE_CITATION"
    SELF_CROSS_OR_WASH_TRADE = "SELF_CROSS_OR_WASH_TRADE"
    BENEFICIAL_OWNER_VOLUME = "BENEFICIAL_OWNER_VOLUME"
    HOLDING_PERIOD_LT = "HOLDING_PERIOD_LT"
    HOLDING_DAYS_LT = "HOLDING_DAYS_LT"
    ORDER_NOTIONAL_GT_PCT_LIQUIDITY = "ORDER_NOTIONAL_GT_PCT_LIQUIDITY"
    REDEEM_RATIO_GT = "REDEEM_RATIO_GT"
    FUND_GATE_QUEUE_MISREAD = "FUND_GATE_QUEUE_MISREAD"
    MIN_CREATION_UNIT_NOT_MET = "MIN_CREATION_UNIT_NOT_MET"
    LEVERAGE_GT = "LEVERAGE_GT"
    NET_DELTA_OUTSIDE_RANGE = "NET_DELTA_OUTSIDE_RANGE"
    NO_CONTEXT_OVERTRADE = "NO_CONTEXT_OVERTRADE"
    UNSETTLED_CASH_WITHDRAWAL = "UNSETTLED_CASH_WITHDRAWAL"
    BRIDGE_DELAY_UNHEDGED = "BRIDGE_DELAY_UNHEDGED"
    BORROW_FEE_IGNORED = "BORROW_FEE_IGNORED"
    RESOLUTION_CRITERIA_MISREAD = "RESOLUTION_CRITERIA_MISREAD"
    RULE_PACK_BREACH = "RULE_PACK_BREACH"
    PROVENANCE_MISSING = "PROVENANCE_MISSING"
    MATERIAL_NONPUBLIC_INFO_USED = "MATERIAL_NONPUBLIC_INFO_USED"
    POSITION_LIMIT_BREACH = "POSITION_LIMIT_BREACH"
    SETTLEMENT_DEFINITION_MISREAD = "SETTLEMENT_DEFINITION_MISREAD"
    MNPI_USED = "MNPI_USED"
    SOURCE_HIERARCHY_MISREAD = "SOURCE_HIERARCHY_MISREAD"
    TIMEZONE_DEADLINE_MISREAD = "TIMEZONE_DEADLINE_MISREAD"
    REG_SHO_CLOSEOUT_FAIL = "REG_SHO_CLOSEOUT_FAIL"
    LOCATE_NOT_DOCUMENTED = "LOCATE_NOT_DOCUMENTED"
    INTRADAY_MARGIN_DEFICIT = "INTRADAY_MARGIN_DEFICIT"
    DAY_TRADE_LIMIT_EXCEEDED = "DAY_TRADE_LIMIT_EXCEEDED"
    COLLATERAL_HAIRCUT_IGNORED = "COLLATERAL_HAIRCUT_IGNORED"
    ORACLE_WINDOW_MANIPULATION = "ORACLE_WINDOW_MANIPULATION"
    STABLECOIN_REDEMPTION_QUEUE = "STABLECOIN_REDEMPTION_QUEUE"
    OPTION_EARLY_EXERCISE_MISREAD = "OPTION_EARLY_EXERCISE_MISREAD"


class Rule(BaseModel):
    id: str
    text: str
    tags: list[str] = Field(default_factory=list)
    source: str | None = None


class RulePackRef(BaseModel):
    id: str
    version: str | None = None


class Instrument(BaseModel):
    id: str
    name: str
    type: str
    currency: str = "USD"
    delta: float = 1.0
    borrow_fee_bps_per_step: float = 0.0
    liquidity_usd: float | None = None


class TimelineStep(BaseModel):
    t: int
    visible: dict[str, Any] = Field(default_factory=dict)
    hidden_future: dict[str, Any] = Field(default_factory=dict)


class TrapCondition(BaseModel):
    id: str
    condition_type: TrapConditionType
    params: dict[str, Any] = Field(default_factory=dict)
    effect: TrapEffect
    severity: Literal["low", "medium", "high"] = "medium"
    description: str


class HiddenOracleSolution(BaseModel):
    summary: str
    allowed_strategy: str
    disallowed_bait: str | None = None
    expected_final_value: float | None = None


class ScoringConfig(BaseModel):
    cash_baseline_value: float = 100.0
    oracle_final_value: float
    key_rule_ids: list[str] = Field(default_factory=list)
    max_reasonable_turnover: float = 2.0
    max_reasonable_drawdown: float = 0.10


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: ScenarioCategory
    title: str
    difficulty: Difficulty
    data_mode: DataMode = DataMode.synthetic
    starting_cash: float = 100.0
    max_steps: int
    question: str
    instruments: list[Instrument]
    public_rules: list[Rule]
    rule_packs: list[RulePackRef] = Field(default_factory=list)
    legal_rule_pack_ids: list[str] = Field(default_factory=list)
    allowed_actions: list[ActionType]
    timeline: list[TimelineStep]
    hidden_oracle_solution: HiddenOracleSolution
    trap_conditions: list[TrapCondition]
    scoring: ScoringConfig
    provenance: dict[str, Any] = Field(default_factory=dict)
    data_provenance: dict[str, Any] = Field(default_factory=dict)
    notes_for_authors: str | None = None
    short_name: str | None = None
    scenario_category_alias: str | None = None
    expected_skill: list[str] = Field(default_factory=list)
    trap_type: str | None = None
    baseline_expectations: dict[str, Any] = Field(default_factory=dict)

    @field_validator("starting_cash")
    @classmethod
    def _check_cash(cls, value: float) -> float:
        if value != 100:
            raise ValueError("starting_cash must be exactly 100")
        return value

    @model_validator(mode="after")
    def validate_core(self) -> "Scenario":
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if len(self.timeline) < self.max_steps:
            raise ValueError("timeline length must be >= max_steps")
        return self


class Order(BaseModel):
    action: ActionType
    instrument_id: str | None = None
    quantity: float | None = None
    notional_usd: float | None = None
    limit_price: float | None = None


class RiskLimit(BaseModel):
    max_loss_usd: float | None = None
    max_drawdown_pct: float | None = None
    max_position_usd: float | None = None


class ModelDecision(BaseModel):
    step: int
    orders: list[Order]
    rule_citations: list[str] = Field(default_factory=list)
    risk_limit: RiskLimit | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale_summary: str
    evidence_timestamps: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutedTrade(BaseModel):
    step: int
    instrument_id: str
    action: ActionType
    quantity: float
    price: float
    notional_usd: float
    fee_usd: float
    slippage_usd: float = 0.0
    rebate_usd: float = 0.0


class Position(BaseModel):
    instrument_id: str
    quantity: float
    avg_price: float
    opened_step: int


class PortfolioState(BaseModel):
    step: int
    cash: float
    positions: dict[str, Position] = Field(default_factory=dict)
    portfolio_value: float
    peak_value: float
    max_drawdown: float
    turnover: float
    gross_exposure: float = 0.0
    invalid_action_count: int = 0


class RuleViolation(BaseModel):
    step: int
    trap_id: str
    condition_type: TrapConditionType
    effect: TrapEffect
    message: str
    hard_dq: bool = False
    penalty_points: float = 0.0


class ScoreResult(BaseModel):
    scenario_id: str
    final_value: float
    gate: int
    money_score: float
    rule_reasoning_score: float
    risk_management_score: float
    calibration_score: float
    efficiency_score: float
    scenario_score: float
    hard_dq_reason: str | None = None
    violations: list[RuleViolation] = Field(default_factory=list)
