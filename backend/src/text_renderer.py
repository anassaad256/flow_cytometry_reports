"""Text rendering with {variable} interpolation and helper clause support."""
from __future__ import annotations

import re
from typing import Any

from .context import EvaluationContext
from .predicates import evaluate_predicate


def _fmt_val(val) -> str:
    """Convert a value to string, stripping trailing zeros from floats."""
    if isinstance(val, float):
        return f"{val:g}"
    return str(val)


def render_text(template_text: str, ctx: EvaluationContext,
                helper_clauses: dict[str, dict] | None = None) -> str:
    """Render a template string by replacing {variable} placeholders with context values."""
    if not template_text:
        return ""

    # First resolve helper clauses
    resolved_clauses: dict[str, str] = {}
    if helper_clauses:
        for clause_name, clause_spec in helper_clauses.items():
            resolved_clauses[clause_name] = _resolve_helper_clause(clause_spec, ctx)

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        # Check helper clauses first
        if var_name in resolved_clauses:
            return resolved_clauses[var_name]
        # Then check context
        val = ctx.get(var_name)
        if val is None:
            return ""
        if isinstance(val, list):
            return ", ".join(_fmt_val(v) for v in val)
        return _fmt_val(val)

    result = re.sub(r"\{(\w+)\}", replacer, template_text)
    # Clean up multi-space runs and normalize whitespace
    result = re.sub(r"[ \t]+", " ", result)
    result = result.strip()
    return result


def _render_clause_text(text: str, ctx: EvaluationContext) -> str:
    """Render clause text preserving intentional leading/trailing spaces."""
    if not text:
        return ""
    # Render variable placeholders but preserve leading/trailing whitespace
    rendered = render_text(text, ctx)
    # Restore leading space if original text had one (stripped by render_text)
    if text[0] == " " and rendered and rendered[0] != " ":
        rendered = " " + rendered
    return rendered


def _resolve_helper_clause(clause_spec: dict, ctx: EvaluationContext) -> str:
    """Resolve a helper clause with conditional text."""
    when = clause_spec.get("when")
    text = clause_spec.get("text", "")
    else_text = clause_spec.get("else_text", "")
    else_when = clause_spec.get("else_when")
    fallback_text = clause_spec.get("fallback_text", "")

    if when and evaluate_predicate(when, ctx):
        return _render_clause_text(text, ctx)
    if else_when and evaluate_predicate(else_when, ctx):
        return _render_clause_text(else_text, ctx) if else_text else ""
    if fallback_text is not None and not else_when:
        return _render_clause_text(else_text, ctx) if else_text else ""
    return _render_clause_text(fallback_text, ctx) if fallback_text else ""


def render_output_lines(output_lines: list, ctx: EvaluationContext) -> list[str]:
    """Render a list of output_lines entries. Each entry can be a string or a transformer dict."""
    result = []
    for entry in output_lines:
        if isinstance(entry, str):
            rendered = render_text(entry, ctx)
            if rendered:
                result.append(rendered)
        elif isinstance(entry, dict):
            if "join_lines" in entry:
                join_spec = entry["join_lines"]
                lists = join_spec.get("lists", [])
                for list_name in lists:
                    val = ctx.get(list_name)
                    if val and isinstance(val, list):
                        for item in val:
                            if isinstance(item, str):
                                result.append(item)
                            elif hasattr(item, "text"):
                                result.append(item.text)
                            elif isinstance(item, dict):
                                result.append(str(item.get("text", "")))
    return result
