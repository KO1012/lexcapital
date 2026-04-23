class LexCapitalError(Exception):
    """Base exception for LexCapital."""


class ScenarioValidationError(LexCapitalError):
    """Scenario file failed validation."""


class ReplayError(LexCapitalError):
    """Replay failed."""


class AdapterError(LexCapitalError):
    """Model adapter failed."""
