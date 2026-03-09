"""Tests for text renderer."""
from src.context import EvaluationContext
from src.text_renderer import render_output_lines, render_text


def make_ctx(**fields):
    ctx = EvaluationContext({})
    ctx.push_scope(fields)
    return ctx


def test_simple_interpolation():
    ctx = make_ctx(name="Alice", age=30)
    assert render_text("Hello {name}, age {age}", ctx) == "Hello Alice, age 30"


def test_missing_variable():
    ctx = make_ctx()
    assert render_text("Value: {missing}", ctx) == "Value:"


def test_list_variable():
    ctx = make_ctx(items=["CD14", "CD13", "CD33"])
    assert render_text("Markers: {items}", ctx) == "Markers: CD14, CD13, CD33"


def test_empty_template():
    ctx = make_ctx()
    assert render_text("", ctx) == ""
    assert render_text(None, ctx) == ""


def test_helper_clause():
    ctx = make_ctx(show_detail=True)
    clauses = {
        "detail_clause": {
            "when": {"field_equals": {"field": "show_detail", "value": True}},
            "text": "with details",
            "else_text": "",
        }
    }
    result = render_text("Report {detail_clause}", ctx, clauses)
    assert "with details" in result


def test_render_output_lines():
    ctx = make_ctx(items=["line1", "line2"])
    lines = render_output_lines(["{items}"], ctx)
    assert lines == ["line1, line2"]
