"""Tests for validation rule engine."""
from src.context import EvaluationContext
from src.validators import run_validations


def test_triggered_validation():
    ctx = EvaluationContext({})
    ctx.push_scope({"status": "BAD"})
    specs = [
        {
            "id": "V_CHECK",
            "severity": "ERROR",
            "message": "Status is bad",
            "when": {"field_equals": {"field": "status", "value": "BAD"}},
        }
    ]
    results = run_validations(specs, ctx)
    assert len(results) == 1
    assert results[0].id == "V_CHECK"
    assert results[0].severity == "ERROR"


def test_not_triggered():
    ctx = EvaluationContext({})
    ctx.push_scope({"status": "GOOD"})
    specs = [
        {
            "id": "V_CHECK",
            "severity": "WARN",
            "message": "Status is bad",
            "when": {"field_equals": {"field": "status", "value": "BAD"}},
        }
    ]
    results = run_validations(specs, ctx)
    assert len(results) == 0


def test_empty_specs():
    ctx = EvaluationContext({})
    assert run_validations([], ctx) == []
