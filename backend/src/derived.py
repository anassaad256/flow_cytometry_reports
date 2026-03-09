"""Derived value computers for the decision tree DSL."""
from __future__ import annotations

from typing import Any

from .context import EvaluationContext
from .models import EXPRESSED_STATES, MARKER_STATE_SUFFIX, MarkerState
from .predicates import evaluate_predicate


def compute_derived(spec: dict, ctx: EvaluationContext) -> Any:
    """Compute a derived value based on its type spec."""
    dtype = spec.get("type")
    # Check enabled_when guard
    enabled_when = spec.get("enabled_when")
    if enabled_when is not None and not evaluate_predicate(enabled_when, ctx):
        # Return empty default for disabled derived values
        if dtype in ("marker_list", "collect_population_outputs"):
            return []
        if dtype in ("ratio_text", "enum_string", "cd4_cd8_status_from_marker_states",
                      "aberrancy_phrase_from_marker_states"):
            return ""
        if dtype in ("population_exists_with_tag", "boolean_or"):
            return False
        return None

    if dtype == "marker_list":
        return compute_marker_list(spec, ctx)
    if dtype == "percent_pick":
        return compute_percent_pick(spec, ctx)
    if dtype == "ratio_text":
        return compute_ratio_text(spec, ctx)
    if dtype == "enum_string":
        return compute_enum_string(spec, ctx)
    if dtype == "cd4_cd8_status_from_marker_states":
        return compute_cd4_cd8_status(spec, ctx)
    if dtype == "aberrancy_phrase_from_marker_states":
        return compute_aberrancy_phrase(spec, ctx)
    if dtype == "population_exists_with_tag":
        return compute_population_exists_with_tag(spec, ctx)
    if dtype == "boolean_or":
        return compute_boolean_or(spec, ctx)
    if dtype == "collect_population_outputs":
        return compute_collect_population_outputs(spec, ctx)
    return None


def compute_marker_list(spec: dict, ctx: EvaluationContext) -> list[str]:
    """Build an ordered, formatted list of marker display names."""
    order_const = spec.get("order_const")
    display_order = ctx.get_constant(order_const) if order_const else []
    if not display_order:
        display_order = []

    # Get include states
    include_states_ref = spec.get("include_states_ref")
    include_states = spec.get("include_states")
    if include_states_ref:
        resolved = ctx.resolve_ref(include_states_ref)
        if resolved:
            include_states = resolved
    if not include_states:
        include_states = []
    include_state_set = set(include_states)

    # Get suffix mapping
    state_suffix_ref = spec.get("state_suffix_ref")
    suffix_map = {}
    if state_suffix_ref:
        resolved = ctx.resolve_ref(state_suffix_ref)
        if resolved and isinstance(resolved, dict):
            suffix_map = resolved

    # Get marker states from context
    marker_states = ctx.get("marker_states")
    if not marker_states:
        return []

    # Build marker_id -> state mapping
    state_map: dict[str, str] = {}
    for ms in marker_states:
        if isinstance(ms, dict):
            state_map[ms["marker_id"]] = ms["state"]
        else:
            state_map[ms.marker_id] = ms.state

    # Get active markers (if set, only include those)
    active_markers = ctx.get("_active_markers")

    # Get marker catalog for display names
    catalog = ctx.get_marker_catalog()

    result = []
    for marker_id in display_order:
        if active_markers and marker_id not in active_markers:
            continue
        state = state_map.get(marker_id)
        if state is None:
            continue
        if state not in include_state_set:
            continue
        # Get display name
        marker_info = catalog.get(marker_id, {})
        display_name = marker_info.get("display", marker_id)
        # Apply suffix if applicable
        suffix = suffix_map.get(state, "")
        if suffix:
            result.append(f"{display_name} ({suffix})")
        else:
            result.append(display_name)
    return result


def compute_percent_pick(spec: dict, ctx: EvaluationContext) -> str:
    """Pick the first available percentage field and format it."""
    preference_fields = spec.get("preference_fields", [])
    precision_ref = spec.get("precision_decimals_ref")
    precision = 1  # default
    if precision_ref:
        resolved = ctx.resolve_ref(precision_ref)
        if resolved is not None:
            precision = int(resolved)

    for field in preference_fields:
        val = ctx.get(field)
        if val is not None:
            try:
                return f"{float(val):.{precision}f}"
            except (ValueError, TypeError):
                continue
    return "0.0"


def compute_ratio_text(spec: dict, ctx: EvaluationContext) -> str:
    """Compute a ratio with directional formatting."""
    num_field = spec.get("numerator_field", "")
    den_field = spec.get("denominator_field", "")
    precision_ref = spec.get("precision_decimals_ref")
    precision = 1
    if precision_ref:
        resolved = ctx.resolve_ref(precision_ref)
        if resolved is not None:
            precision = int(resolved)

    num_val = ctx.get(num_field)
    den_val = ctx.get(den_field)
    if num_val is None or den_val is None:
        return ""
    try:
        num = float(num_val)
        den = float(den_val)
    except (ValueError, TypeError):
        return ""
    if den == 0 and num == 0:
        return "1.0:1"

    fmt = spec.get("format", {})
    # Determine direction - handle both kappa/lambda and cd4/cd8 naming
    format_keys = list(fmt.keys())
    if len(format_keys) >= 2:
        ge_key = format_keys[0]  # "if_kappa_ge_lambda" or "if_cd4_ge_cd8"
        gt_key = format_keys[1]  # "if_lambda_gt_kappa" or "if_cd8_gt_cd4"
    else:
        ge_key = "if_kappa_ge_lambda"
        gt_key = "if_lambda_gt_kappa"

    if num >= den:
        ratio = num / den if den > 0 else num
        template = fmt.get(ge_key, "{ratio}:1")
    else:
        ratio = den / num if num > 0 else den
        template = fmt.get(gt_key, "1:{ratio}")

    ratio_str = f"{ratio:.{precision}f}"
    return template.replace("{ratio}", ratio_str)


def compute_enum_string(spec: dict, ctx: EvaluationContext) -> str:
    """Map a tag or field value to a display string."""
    values = spec.get("values", {})
    # Check if any tag matches
    for tag_or_value, display in values.items():
        if ctx.has_tag(tag_or_value):
            return display
    # Check if any field matches
    for tag_or_value, display in values.items():
        for scope in reversed(ctx._scopes):
            for v in scope.values():
                if v == tag_or_value:
                    return display
    return ""


def compute_cd4_cd8_status(spec: dict, ctx: EvaluationContext) -> str:
    """Determine CD4/CD8 status phrase from marker states."""
    cd4_marker = spec.get("cd4_marker", "M_CD4")
    cd8_marker = spec.get("cd8_marker", "M_CD8")
    expressed_ref = spec.get("expressed_states_ref")
    neg_state = spec.get("negative_state", "STATE_NEGATIVE")
    na_state = spec.get("na_state", "STATE_NA")
    phrases = spec.get("phrases", {})

    expressed_states = set()
    if expressed_ref:
        resolved = ctx.resolve_ref(expressed_ref)
        if resolved:
            expressed_states = set(resolved)

    marker_states = ctx.get("marker_states")
    if not marker_states:
        return phrases.get("indeterminate", "")

    state_map: dict[str, str] = {}
    for ms in marker_states:
        if isinstance(ms, dict):
            state_map[ms["marker_id"]] = ms["state"]
        else:
            state_map[ms.marker_id] = ms.state

    cd4_state = state_map.get(cd4_marker)
    cd8_state = state_map.get(cd8_marker)

    if cd4_state == na_state or cd8_state == na_state:
        return phrases.get("indeterminate", "")

    cd4_pos = cd4_state in expressed_states
    cd8_pos = cd8_state in expressed_states
    cd4_neg = cd4_state == neg_state
    cd8_neg = cd8_state == neg_state

    if cd4_pos and cd8_neg:
        return phrases.get("cd4_pos_cd8_neg", "CD4-positive")
    if cd4_neg and cd8_pos:
        return phrases.get("cd4_neg_cd8_pos", "CD8-positive")
    if cd4_pos and cd8_pos:
        return phrases.get("double_positive", "CD4/CD8 double-positive")
    if cd4_neg and cd8_neg:
        return phrases.get("double_negative", "CD4/CD8 double-negative")
    return phrases.get("indeterminate", "")


def compute_aberrancy_phrase(spec: dict, ctx: EvaluationContext) -> str:
    """Find first aberrant marker and generate a descriptive phrase."""
    priority_markers = spec.get("priority_markers", [])
    normal_states = set(spec.get("normal_states", []))
    ignore_states = set(spec.get("ignore_states", []))
    mapping = spec.get("mapping", {})
    fallback = spec.get("fallback", "showing an aberrant immunophenotype")

    marker_states = ctx.get("marker_states")
    if not marker_states:
        return fallback

    state_map: dict[str, str] = {}
    for ms in marker_states:
        if isinstance(ms, dict):
            state_map[ms["marker_id"]] = ms["state"]
        else:
            state_map[ms.marker_id] = ms.state

    catalog = ctx.get_marker_catalog()

    for marker_id in priority_markers:
        state = state_map.get(marker_id)
        if state is None or state in ignore_states or state in normal_states:
            continue
        template = mapping.get(state, fallback)
        marker_info = catalog.get(marker_id, {})
        display = marker_info.get("display", marker_id)
        return template.replace("{marker_display}", display)

    return fallback


def compute_population_exists_with_tag(spec: dict, ctx: EvaluationContext) -> bool:
    """Check if any population instance has a specific tag."""
    args = spec.get("args", {})
    tag = args.get("tag", "")
    return ctx.population_exists_with_tag(tag)


def compute_boolean_or(spec: dict, ctx: EvaluationContext) -> bool:
    """OR together multiple derived boolean values."""
    args = spec.get("args", {})
    values = args.get("values", [])
    return any(bool(ctx.get(v)) for v in values)


def compute_collect_population_outputs(spec: dict, ctx: EvaluationContext) -> list:
    """Collect outputs from all instances of a population type."""
    args = spec.get("args", {})
    population_id = args.get("population_id", "")
    output_kind = args.get("output_kind", "")
    return ctx.collect_population_outputs(population_id, output_kind)
