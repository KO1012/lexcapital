class FinRuleBenchError(Exception):
    """Base exception for FinRuleBench."""


class ScenarioValidationError(FinRuleBenchError):
    """Scenario file failed validation."""


class ReplayError(FinRuleBenchError):
    """Replay failed."""


class AdapterError(FinRuleBenchError):
    """Model adapter failed."""
