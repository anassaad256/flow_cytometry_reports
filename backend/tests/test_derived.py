"""Tests for derived value computers."""
from src.context import EvaluationContext
from src.derived import compute_derived


def make_ctx(main_tree=None, **fields):
    ctx = EvaluationContext(main_tree or {})
    ctx.push_scope(fields)
    return ctx


def test_percent_pick():
    ctx = make_ctx(pct_gated_events=45.3)
    result = compute_derived(
        {"type": "percent_pick", "preference_fields": ["pct_gated_events"]},
        ctx,
    )
    assert result == "45.3"


def test_percent_pick_fallback():
    ctx = make_ctx()
    result = compute_derived(
        {"type": "percent_pick", "preference_fields": ["missing_field"]},
        ctx,
    )
    assert result == "0"


def test_enum_string_from_tag():
    ctx = make_ctx()
    ctx.add_tag("BLAST_MYELOBLASTS")
    result = compute_derived(
        {"type": "enum_string", "values": {
            "BLAST_MYELOBLASTS": "myeloblasts",
            "BLAST_B_LYMPHOBLASTS": "B lymphoblasts",
        }},
        ctx,
    )
    assert result == "myeloblasts"


def test_marker_list():
    ctx = make_ctx(
        marker_states=[
            {"marker_id": "M_CD13", "state": "STATE_POSITIVE"},
            {"marker_id": "M_CD14", "state": "STATE_NEGATIVE"},
        ],
    )
    ctx.set_current_panel_spec({
        "constants": {"display_order": ["M_CD14", "M_CD13"]},
        "marker_catalog": {
            "M_CD13": {"display": "CD13"},
            "M_CD14": {"display": "CD14"},
        },
    })
    result = compute_derived(
        {
            "type": "marker_list",
            "order_const": "display_order",
            "include_states": ["STATE_POSITIVE"],
        },
        ctx,
    )
    assert result == ["CD13"]


def test_enabled_when_disabled():
    ctx = make_ctx(flag="NO")
    result = compute_derived(
        {
            "type": "marker_list",
            "enabled_when": {"field_equals": {"field": "flag", "value": "YES"}},
        },
        ctx,
    )
    assert result == []


def test_ratio_text():
    ctx = make_ctx(num=4.0, den=2.0)
    result = compute_derived(
        {
            "type": "ratio_text",
            "numerator_field": "num",
            "denominator_field": "den",
            "format": {"if_num_ge_den": "{ratio}:1", "if_den_gt_num": "1:{ratio}"},
        },
        ctx,
    )
    assert result == "2:1"


def test_population_exists_with_tag():
    ctx = make_ctx()
    ctx.store_population_tags("POP_A", {"my_tag"})
    result = compute_derived(
        {"type": "population_exists_with_tag", "args": {"tag": "my_tag"}},
        ctx,
    )
    assert result is True


def test_boolean_or():
    ctx = make_ctx(a=False, b=True)
    result = compute_derived(
        {"type": "boolean_or", "args": {"values": ["a", "b"]}},
        ctx,
    )
    assert result is True


def test_unknown_type():
    ctx = make_ctx()
    assert compute_derived({"type": "nonexistent"}, ctx) is None
