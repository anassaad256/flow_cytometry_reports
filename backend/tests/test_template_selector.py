"""Tests for template selector."""
from src.context import EvaluationContext
from src.template_selector import select_all_matching_templates, select_template


def make_ctx(**fields):
    ctx = EvaluationContext({})
    ctx.push_scope(fields)
    return ctx


def test_select_highest_priority():
    templates = [
        {"priority": 50, "when": {"default": True}, "text": "low"},
        {"priority": 100, "when": {"default": True}, "text": "high"},
    ]
    ctx = make_ctx()
    result = select_template(templates, ctx)
    assert result["text"] == "high"


def test_select_skips_non_matching():
    templates = [
        {"priority": 100, "when": {"field_equals": {"field": "x", "value": "A"}}, "text": "A"},
        {"priority": 50, "when": {"default": True}, "text": "fallback"},
    ]
    ctx = make_ctx(x="B")
    result = select_template(templates, ctx)
    assert result["text"] == "fallback"


def test_select_no_match():
    templates = [
        {"priority": 100, "when": {"field_equals": {"field": "x", "value": "A"}}, "text": "A"},
    ]
    ctx = make_ctx(x="B")
    assert select_template(templates, ctx) is None


def test_select_template_without_when():
    templates = [{"priority": 10, "text": "unconditional"}]
    ctx = make_ctx()
    result = select_template(templates, ctx)
    assert result["text"] == "unconditional"


def test_select_all_matching():
    templates = [
        {"priority": 100, "when": {"default": True}, "text": "A"},
        {"priority": 50, "when": {"default": True}, "text": "B"},
        {"priority": 75, "when": {"field_equals": {"field": "x", "value": "Z"}}, "text": "C"},
    ]
    ctx = make_ctx(x="Y")
    results = select_all_matching_templates(templates, ctx)
    assert [r["text"] for r in results] == ["A", "B"]
