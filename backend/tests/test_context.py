"""Tests for EvaluationContext."""
from src.context import EvaluationContext


def test_scope_push_pop():
    ctx = EvaluationContext({})
    ctx.push_scope({"a": 1})
    assert ctx.get("a") == 1
    ctx.push_scope({"b": 2})
    assert ctx.get("a") == 1
    assert ctx.get("b") == 2
    ctx.pop_scope()
    assert ctx.get("b") is None
    assert ctx.get("a") == 1


def test_scope_shadowing():
    ctx = EvaluationContext({})
    ctx.push_scope({"x": "outer"})
    ctx.push_scope({"x": "inner"})
    assert ctx.get("x") == "inner"
    ctx.pop_scope()
    assert ctx.get("x") == "outer"


def test_has():
    ctx = EvaluationContext({})
    assert not ctx.has("x")
    ctx.push_scope({"x": None})
    assert ctx.has("x")


def test_set_derived():
    ctx = EvaluationContext({})
    ctx.push_scope({})
    ctx.set_derived("foo", 42)
    assert ctx.get("foo") == 42


def test_get_constant_from_main_tree():
    ctx = EvaluationContext({"constants": {"threshold": 50}})
    assert ctx.get_constant("threshold") == 50


def test_get_constant_from_panel_spec():
    ctx = EvaluationContext({"constants": {"threshold": 50}})
    ctx.set_current_panel_spec({"constants": {"threshold": 99}})
    assert ctx.get_constant("threshold") == 99


def test_tags():
    ctx = EvaluationContext({})
    assert not ctx.has_tag("foo")
    ctx.add_tag("foo")
    assert ctx.has_tag("foo")
    ctx.add_tags(["bar", "baz"])
    assert ctx.has_any_tag(["bar"])
    assert ctx.has_any_tag(["missing", "baz"])
    assert not ctx.has_any_tag(["missing"])
    tags = ctx.get_tags()
    assert tags == {"foo", "bar", "baz"}
    ctx.clear_tags()
    assert not ctx.has_tag("foo")


def test_population_tags():
    ctx = EvaluationContext({})
    ctx.store_population_tags("POP_A", {"tag1", "tag2"})
    ctx.store_population_tags("POP_A", {"tag3"})
    ctx.store_population_tags("POP_B", {"tag1"})
    assert ctx.population_exists_with_tag("tag1")
    assert not ctx.population_exists_with_tag("tag_missing")
    assert ctx.count_populations_with_tag("tag1") == 2
    assert ctx.count_populations_with_tag("tag3") == 1
    assert ctx.count_populations_with_any_tag(["tag2", "tag3"]) == 2


def test_population_outputs():
    ctx = EvaluationContext({})
    ctx.store_population_output("POP_A", "comment_line", ["line1"])
    ctx.store_population_output("POP_A", "comment_line", ["line2"])
    assert ctx.collect_population_outputs("POP_A", "comment_line") == ["line1", "line2"]
    assert ctx.collect_population_outputs("POP_A", "main_line_item") == []
    ctx.clear_population_state()
    assert ctx.collect_population_outputs("POP_A", "comment_line") == []


def test_marker_catalog():
    ctx = EvaluationContext({})
    assert ctx.get_marker_catalog() == {}
    ctx.set_current_panel_spec({"marker_catalog": {"M_CD14": {"display": "CD14"}}})
    assert ctx.get_marker_catalog() == {"M_CD14": {"display": "CD14"}}
