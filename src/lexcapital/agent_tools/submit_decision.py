from lexcapital.core.models import ModelDecision


def submit_decision(decision):
    return ModelDecision.model_validate(decision)
