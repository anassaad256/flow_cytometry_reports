"""Tag computation engine for the lymphoproliferative panel."""
from __future__ import annotations

from typing import Any

from .context import EvaluationContext
from .predicates import evaluate_predicate


def compute_tags(population_spec: dict, ctx: EvaluationContext) -> set[str]:
    """Compute all tags for a population instance.

    Tag sources:
    1. Static tags (always applied)
    2. from_fields tags (based on field values)
    3. auto_from_markers tags (auto-generated from marker states)
    """
    tags_spec = population_spec.get("tags")
    if not tags_spec:
        return set()

    tags: set[str] = set()

    # 1. Static tags
    static = tags_spec.get("static", [])
    tags.update(static)

    # 2. from_fields tags
    from_fields = tags_spec.get("from_fields", [])
    for ff in from_fields:
        when = ff.get("when")
        if when and evaluate_predicate(when, ctx):
            set_tags = ff.get("set_tags", [])
            tags.update(set_tags)

    # 3. auto_from_markers tags
    auto_spec = tags_spec.get("auto_from_markers")
    if auto_spec:
        tags.update(_compute_auto_marker_tags(auto_spec, ctx))

    return tags


def _compute_auto_marker_tags(auto_spec: dict, ctx: EvaluationContext) -> set[str]:
    """Generate tags automatically from marker states."""
    expressed_pattern = auto_spec.get("expressed_tag_pattern", "")
    negative_pattern = auto_spec.get("negative_tag_pattern", "")
    modifier_patterns = auto_spec.get("modifier_tag_patterns", {})

    marker_states = ctx.get("marker_states")
    if not marker_states:
        return set()

    # Get expressed states from main tree
    expressed_states = set()
    expressed_ref = ctx.resolve_ref("shared_refs.expressed_states_ref")
    if expressed_ref:
        expressed_states = set(expressed_ref)

    tags: set[str] = set()
    active_markers = ctx.get("_active_markers")

    for ms in marker_states:
        if isinstance(ms, dict):
            marker_id, state = ms["marker_id"], ms["state"]
        else:
            marker_id, state = ms.marker_id, ms.state

        if active_markers and marker_id not in active_markers:
            continue

        # Strip M_ prefix for tag substitution
        marker_short = marker_id
        if marker_short.startswith("M_"):
            marker_short = marker_short[2:]

        if state == "STATE_NEGATIVE":
            if negative_pattern:
                tags.add(negative_pattern.replace("{marker}", marker_short))
        elif state in expressed_states:
            if expressed_pattern:
                tags.add(expressed_pattern.replace("{marker}", marker_short))
            # Check for modifier-specific tags
            modifier_tag = modifier_patterns.get(state, "")
            if modifier_tag:
                tags.add(modifier_tag.replace("{marker}", marker_short))

    return tags


def evaluate_rules(rules: list[dict], ctx: EvaluationContext) -> set[str]:
    """Evaluate rule-based tags for a population.

    Tags are added to the context incrementally so later rules can
    depend on tags set by earlier rules.
    """
    new_tags: set[str] = set()
    for rule in rules:
        when = rule.get("when")
        if when and evaluate_predicate(when, ctx):
            set_tags = rule.get("set_tags", [])
            new_tags.update(set_tags)
            ctx.add_tags(set(set_tags))
    return new_tags


def apply_normalizations(normalizations: list[dict], ctx: EvaluationContext) -> None:
    """Apply normalizations that set field values based on tag conditions."""
    for norm in normalizations:
        when = norm.get("when")
        if when and evaluate_predicate(when, ctx):
            set_fields = norm.get("set_fields", {})
            for field, value in set_fields.items():
                ctx.set_derived(field, value)
