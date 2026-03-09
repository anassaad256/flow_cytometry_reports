"""Tests for predicate evaluators."""
from src.context import EvaluationContext
from src.predicates import evaluate_predicate


def make_ctx(**fields):
    ctx = EvaluationContext({})
    ctx.push_scope(fields)
    return ctx


def test_bool_literal():
    ctx = make_ctx()
    assert evaluate_predicate(True, ctx) is True
    assert evaluate_predicate(False, ctx) is False


def test_default():
    ctx = make_ctx()
    assert evaluate_predicate({"default": True}, ctx) is True
    assert evaluate_predicate({"default": False}, ctx) is False


def test_field_equals():
    ctx = make_ctx(status="ACTIVE")
    assert evaluate_predicate({"field_equals": {"field": "status", "value": "ACTIVE"}}, ctx)
    assert not evaluate_predicate({"field_equals": {"field": "status", "value": "INACTIVE"}}, ctx)


def test_field_present():
    ctx = make_ctx(x=42)
    assert evaluate_predicate({"field_present": "x"}, ctx)
    assert not evaluate_predicate({"field_present": "y"}, ctx)


def test_field_gte_and_lt():
    ctx = make_ctx(pct=75.0)
    assert evaluate_predicate({"field_gte": {"field": "pct", "value": 50}}, ctx)
    assert not evaluate_predicate({"field_gte": {"field": "pct", "value": 80}}, ctx)
    assert evaluate_predicate({"field_lt": {"field": "pct", "value": 80}}, ctx)
    assert not evaluate_predicate({"field_lt": {"field": "pct", "value": 50}}, ctx)


def test_list_nonempty():
    ctx = make_ctx(items=[1, 2], empty=[], s="hello", blank="")
    assert evaluate_predicate({"list_nonempty": "items"}, ctx)
    assert not evaluate_predicate({"list_nonempty": "empty"}, ctx)
    assert evaluate_predicate({"list_nonempty": "s"}, ctx)
    assert not evaluate_predicate({"list_nonempty": "blank"}, ctx)
    assert not evaluate_predicate({"list_nonempty": "missing"}, ctx)


def test_all_any_not():
    ctx = make_ctx(a=True, b=False)
    assert evaluate_predicate({"all": [{"field_present": "a"}, {"default": True}]}, ctx)
    assert not evaluate_predicate({"all": [{"field_present": "a"}, {"field_present": "c"}]}, ctx)
    assert evaluate_predicate({"any": [{"field_present": "c"}, {"field_present": "a"}]}, ctx)
    assert not evaluate_predicate({"any": [{"field_present": "c"}, {"field_present": "d"}]}, ctx)
    assert evaluate_predicate({"not": {"field_present": "c"}}, ctx)


def test_marker_state_is():
    ctx = make_ctx(marker_states=[
        {"marker_id": "M_CD14", "state": "STATE_POSITIVE"},
        {"marker_id": "M_CD13", "state": "STATE_NEGATIVE"},
    ])
    assert evaluate_predicate(
        {"marker_state_is": {"marker": "M_CD14", "state": "STATE_POSITIVE"}}, ctx
    )
    assert not evaluate_predicate(
        {"marker_state_is": {"marker": "M_CD14", "state": "STATE_NEGATIVE"}}, ctx
    )


def test_marker_states_all_equal():
    ctx = make_ctx(marker_states=[
        {"marker_id": "M_CD14", "state": "STATE_NA"},
        {"marker_id": "M_CD13", "state": "STATE_NA"},
    ])
    assert evaluate_predicate({"marker_states_all_equal": {"state": "STATE_NA"}}, ctx)
    assert not evaluate_predicate({"marker_states_all_equal": {"state": "STATE_POSITIVE"}}, ctx)


def test_tag_predicates():
    ctx = make_ctx()
    ctx.add_tags(["T_POSITIVE", "T_BRIGHT"])
    assert evaluate_predicate({"tag_present": "T_POSITIVE"}, ctx)
    assert not evaluate_predicate({"tag_present": "T_MISSING"}, ctx)
    assert evaluate_predicate({"any_tag": ["T_MISSING", "T_BRIGHT"]}, ctx)
    assert not evaluate_predicate({"any_tag": ["T_MISSING", "T_GONE"]}, ctx)


def test_population_count_predicates():
    ctx = make_ctx()
    ctx.store_population_tags("POP_A", {"tag_x"})
    ctx.store_population_tags("POP_A", {"tag_x"})
    assert evaluate_predicate(
        {"population_count_with_tag": {"tag": "tag_x", "op": "gte", "value": 2}}, ctx
    )
    assert not evaluate_predicate(
        {"population_count_with_tag": {"tag": "tag_x", "op": "gte", "value": 3}}, ctx
    )


def test_unknown_predicate_returns_false():
    ctx = make_ctx()
    assert evaluate_predicate({"unknown_op": "whatever"}, ctx) is False
    assert evaluate_predicate(42, ctx) is False
