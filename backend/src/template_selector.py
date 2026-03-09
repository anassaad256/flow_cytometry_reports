"""Priority-ordered template selection engine."""
from __future__ import annotations

from typing import Any

from .context import EvaluationContext
from .predicates import evaluate_predicate


def select_template(templates: list[dict], ctx: EvaluationContext) -> dict | None:
    """Select the highest-priority template whose `when` predicate matches.

    Templates are sorted by priority descending; first match wins.
    """
    sorted_templates = sorted(templates, key=lambda t: t.get("priority", 0), reverse=True)
    for template in sorted_templates:
        when = template.get("when")
        if when is None:
            return template
        if evaluate_predicate(when, ctx):
            return template
    return None


def select_all_matching_templates(templates: list[dict], ctx: EvaluationContext) -> list[dict]:
    """Select all templates whose `when` predicate matches, sorted by priority descending."""
    sorted_templates = sorted(templates, key=lambda t: t.get("priority", 0), reverse=True)
    return [t for t in sorted_templates if evaluate_predicate(t.get("when", {"default": True}), ctx)]
