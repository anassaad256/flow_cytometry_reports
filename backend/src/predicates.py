"""Predicate evaluators for the decision tree DSL."""
from __future__ import annotations

from typing import Any

from .context import EvaluationContext
from .models import EXPRESSED_STATES, MarkerState


def evaluate_predicate(pred_spec: Any, ctx: EvaluationContext) -> bool:
    """Top-level dispatcher for predicate evaluation."""
    if isinstance(pred_spec, bool):
        return pred_spec

    if isinstance(pred_spec, str):
        # A bare string might be a reference to a derived boolean
        val = ctx.get(pred_spec)
        return bool(val) if val is not None else False

    if not isinstance(pred_spec, dict):
        return False

    if "all" in pred_spec:
        return pred_all(pred_spec["all"], ctx)
    if "any" in pred_spec:
        return pred_any(pred_spec["any"], ctx)
    if "not" in pred_spec:
        return pred_not(pred_spec["not"], ctx)
    if "default" in pred_spec:
        return bool(pred_spec["default"])
    if "field_present" in pred_spec:
        return pred_field_present(pred_spec["field_present"], ctx)
    if "field_equals" in pred_spec:
        return pred_field_equals(pred_spec["field_equals"], ctx)
    if "field_gte" in pred_spec:
        return pred_field_gte(pred_spec["field_gte"], ctx)
    if "field_lt" in pred_spec:
        return pred_field_lt(pred_spec["field_lt"], ctx)
    if "list_nonempty" in pred_spec:
        return pred_list_nonempty(pred_spec["list_nonempty"], ctx)
    if "marker_states_all_equal" in pred_spec:
        return pred_marker_states_all_equal(pred_spec["marker_states_all_equal"], ctx)
    if "marker_states_all_na_except" in pred_spec:
        return pred_marker_states_all_na_except(pred_spec["marker_states_all_na_except"], ctx)
    if "marker_state_is" in pred_spec:
        return pred_marker_state_is(pred_spec["marker_state_is"], ctx)
    if "marker_state_in" in pred_spec:
        return pred_marker_state_in(pred_spec["marker_state_in"], ctx)
    if "context_region_equals" in pred_spec:
        return pred_context_region_equals(pred_spec["context_region_equals"], ctx)
    if "context_population_equals" in pred_spec:
        return pred_context_population_equals(pred_spec["context_population_equals"], ctx)
    if "tag_present" in pred_spec:
        return pred_tag_present(pred_spec["tag_present"], ctx)
    if "any_tag" in pred_spec:
        return pred_any_tag(pred_spec["any_tag"], ctx)
    if "population_count_with_tag" in pred_spec:
        return pred_population_count_with_tag(pred_spec["population_count_with_tag"], ctx)
    if "population_count_with_tag_any" in pred_spec:
        return pred_population_count_with_tag_any(pred_spec["population_count_with_tag_any"], ctx)

    return False


def pred_all(children: list, ctx: EvaluationContext) -> bool:
    return all(evaluate_predicate(child, ctx) for child in children)


def pred_any(children: list, ctx: EvaluationContext) -> bool:
    return any(evaluate_predicate(child, ctx) for child in children)


def pred_not(child: Any, ctx: EvaluationContext) -> bool:
    return not evaluate_predicate(child, ctx)


def pred_field_present(field: str, ctx: EvaluationContext) -> bool:
    return ctx.has(field) and ctx.get(field) is not None


def pred_field_equals(spec: dict, ctx: EvaluationContext) -> bool:
    field = spec["field"]
    value = spec["value"]
    return ctx.get(field) == value


def pred_field_gte(spec: dict, ctx: EvaluationContext) -> bool:
    field = spec["field"]
    value = spec["value"]
    field_val = ctx.get(field)
    if field_val is None:
        return False
    try:
        return float(field_val) >= float(value)
    except (ValueError, TypeError):
        return False


def pred_field_lt(spec: dict, ctx: EvaluationContext) -> bool:
    field = spec["field"]
    value = spec["value"]
    field_val = ctx.get(field)
    if field_val is None:
        return False
    try:
        return float(field_val) < float(value)
    except (ValueError, TypeError):
        return False


def pred_list_nonempty(field: str, ctx: EvaluationContext) -> bool:
    val = ctx.get(field)
    if val is None:
        return False
    if isinstance(val, (list, str)):
        return len(val) > 0
    return bool(val)


def pred_marker_states_all_equal(spec: dict, ctx: EvaluationContext) -> bool:
    """Check if all marker states equal a specific state."""
    target_state = spec["state"]
    marker_states = ctx.get("marker_states")
    if not marker_states:
        return False
    if isinstance(marker_states, list):
        return all(
            (ms.get("state") if isinstance(ms, dict) else ms.state) == target_state
            for ms in marker_states
        )
    return False


def pred_marker_states_all_na_except(spec: dict, ctx: EvaluationContext) -> bool:
    """Check if all markers are NA except the specified exceptions."""
    except_markers = set(spec.get("except", []))
    marker_states = ctx.get("marker_states")
    if not marker_states:
        return False
    for ms in marker_states:
        if isinstance(ms, dict):
            mid, state = ms["marker_id"], ms["state"]
        else:
            mid, state = ms.marker_id, ms.state
        if mid not in except_markers and state != MarkerState.NA.value:
            return False
    return True


def pred_marker_state_is(spec: dict, ctx: EvaluationContext) -> bool:
    """Check if a specific marker has a specific state."""
    marker = spec["marker"]
    target_state = spec["state"]
    marker_states = ctx.get("marker_states")
    if not marker_states:
        return False
    for ms in marker_states:
        if isinstance(ms, dict):
            mid, state = ms["marker_id"], ms["state"]
        else:
            mid, state = ms.marker_id, ms.state
        if mid == marker:
            return state == target_state
    return False


def pred_marker_state_in(spec: dict, ctx: EvaluationContext) -> bool:
    """Check if a specific marker's state is in a set of states."""
    marker = spec["marker"]
    # States can come from a ref or directly
    states = spec.get("states")
    states_ref = spec.get("states_ref")
    if states_ref:
        resolved = ctx.resolve_ref(states_ref)
        if resolved:
            states = resolved
    if not states:
        return False
    # Convert state enum values to strings for comparison
    state_values = set()
    for s in states:
        if isinstance(s, str):
            state_values.add(s)
        else:
            state_values.add(s.value if hasattr(s, 'value') else str(s))

    marker_states = ctx.get("marker_states")
    if not marker_states:
        return False
    for ms in marker_states:
        if isinstance(ms, dict):
            mid, state = ms["marker_id"], ms["state"]
        else:
            mid, state = ms.marker_id, ms.state
        if mid == marker:
            return state in state_values
    return False


def pred_context_region_equals(region_id: str, ctx: EvaluationContext) -> bool:
    return ctx.get("_current_region") == region_id


def pred_context_population_equals(population_id: str, ctx: EvaluationContext) -> bool:
    return ctx.get("_current_population") == population_id


def pred_tag_present(tag: str, ctx: EvaluationContext) -> bool:
    return ctx.has_tag(tag)


def pred_any_tag(tags: list[str], ctx: EvaluationContext) -> bool:
    return ctx.has_any_tag(tags)


def pred_population_count_with_tag(spec: dict, ctx: EvaluationContext) -> bool:
    tag = spec.get("tag", "")
    op = spec.get("op", "gte")
    value = spec.get("value", 1)
    count = ctx.count_populations_with_tag(tag)
    if op == "gte":
        return count >= value
    if op == "eq":
        return count == value
    if op == "gt":
        return count > value
    if op == "lt":
        return count < value
    return count >= value


def pred_population_count_with_tag_any(spec: dict, ctx: EvaluationContext) -> bool:
    tags = spec.get("tags", [])
    op = spec.get("op", "gte")
    value = spec.get("value", 1)
    count = ctx.count_populations_with_any_tag(tags)
    if op == "gte":
        return count >= value
    if op == "eq":
        return count == value
    return count >= value
