"""Validation rule engine."""
from __future__ import annotations

from .context import EvaluationContext
from .models import ValidationResult
from .predicates import evaluate_predicate


def run_validations(validation_specs: list[dict], ctx: EvaluationContext) -> list[ValidationResult]:
    """Evaluate a list of validation rules and return triggered results."""
    results = []
    for spec in validation_specs:
        when = spec.get("when")
        if when and evaluate_predicate(when, ctx):
            results.append(ValidationResult(
                id=spec.get("id", "UNKNOWN"),
                severity=spec.get("severity", "ERROR"),
                message=spec.get("message", "Validation error"),
            ))
    return results
