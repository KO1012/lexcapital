class LexcapitalError(Exception):
    """Base exception for lexcapital."""


class ScenarioValidationError(LexcapitalError):
    """Scenario file failed validation."""


class ReplayError(LexcapitalError):
    """Replay failed."""


class AdapterError(LexcapitalError):
    """Model adapter failed."""
