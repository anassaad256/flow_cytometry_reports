"""Evaluation context with hierarchical scope stack and tag store."""
from __future__ import annotations

from typing import Any


class EvaluationContext:
    """Hierarchical scoped context for variable resolution during tree evaluation."""

    def __init__(self, main_tree_spec: dict, panel_specs: dict[str, dict] | None = None):
        self._main_tree = main_tree_spec
        self._panel_specs = panel_specs or {}
        self._scopes: list[dict[str, Any]] = []
        self._tags: set[str] = set()
        # Per-population tag storage: list of (population_id, tags_set) tuples
        self._population_tags: list[tuple[str, set[str]]] = []
        # Population outputs: list of (population_id, output_kind, value) tuples
        self._population_outputs: list[tuple[str, str, Any]] = []
        # Current panel spec reference
        self._current_panel_spec: dict | None = None

    def push_scope(self, scope: dict[str, Any]) -> None:
        self._scopes.append(scope)

    def pop_scope(self) -> dict[str, Any]:
        return self._scopes.pop()

    def get(self, field: str) -> Any:
        """Walk scopes bottom-up to find a field value."""
        for scope in reversed(self._scopes):
            if field in scope:
                return scope[field]
        return None

    def has(self, field: str) -> bool:
        for scope in reversed(self._scopes):
            if field in scope:
                return True
        return False

    def set_derived(self, key: str, value: Any) -> None:
        if self._scopes:
            self._scopes[-1][key] = value

    def get_constant(self, name: str) -> Any:
        """Resolve a constant from the current panel spec or main tree."""
        if self._current_panel_spec:
            constants = self._current_panel_spec.get("constants", {})
            if name in constants:
                return constants[name]
        constants = self._main_tree.get("constants", {})
        return constants.get(name)

    def get_marker_catalog(self) -> dict:
        """Get marker catalog from current panel spec."""
        if self._current_panel_spec:
            return self._current_panel_spec.get("marker_catalog", {})
        return {}

    def resolve_ref(self, ref: str) -> Any:
        """Resolve dot-notation references like 'shared_refs.expressed_states_ref'."""
        if ref.startswith("shared_refs."):
            ref_key = ref.split(".", 1)[1]
            if self._current_panel_spec:
                shared_refs = self._current_panel_spec.get("shared_refs", {})
                target_ref = shared_refs.get(ref_key, "")
            else:
                target_ref = ""
            return self._resolve_main_tree_ref(target_ref)
        return self._resolve_main_tree_ref(ref)

    def _resolve_main_tree_ref(self, ref: str) -> Any:
        """Resolve a reference path in the main tree spec."""
        prefix = "flow_cytometry_main_tree_v2."
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
        parts = ref.split(".")
        obj: Any = self._main_tree
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return None
        return obj

    def set_current_panel_spec(self, spec: dict | None) -> None:
        self._current_panel_spec = spec

    # ── Tag management ────────────────────────────────────────────────────────

    def add_tag(self, tag: str) -> None:
        self._tags.add(tag)

    def add_tags(self, tags: list[str] | set[str]) -> None:
        self._tags.update(tags)

    def has_tag(self, tag: str) -> bool:
        return tag in self._tags

    def has_any_tag(self, tags: list[str]) -> bool:
        return bool(self._tags.intersection(tags))

    def clear_tags(self) -> None:
        self._tags.clear()

    def get_tags(self) -> set[str]:
        return set(self._tags)

    # ── Population tag tracking ───────────────────────────────────────────────

    def store_population_tags(self, population_id: str, tags: set[str]) -> None:
        self._population_tags.append((population_id, tags))

    def get_all_population_tags(self) -> list[tuple[str, set[str]]]:
        return list(self._population_tags)

    def population_exists_with_tag(self, tag: str) -> bool:
        return any(tag in tags for _, tags in self._population_tags)

    def count_populations_with_tag(self, tag: str) -> int:
        return sum(1 for _, tags in self._population_tags if tag in tags)

    def count_populations_with_any_tag(self, tag_list: list[str]) -> int:
        tag_set = set(tag_list)
        return sum(1 for _, tags in self._population_tags if tags.intersection(tag_set))

    # ── Population output tracking ────────────────────────────────────────────

    def store_population_output(self, population_id: str, output_kind: str, value: Any) -> None:
        self._population_outputs.append((population_id, output_kind, value))

    def collect_population_outputs(self, population_id: str, output_kind: str) -> list:
        results = []
        for pid, kind, value in self._population_outputs:
            if pid == population_id and kind == output_kind:
                if isinstance(value, list):
                    results.extend(value)
                else:
                    results.append(value)
        return results

    def clear_population_state(self) -> None:
        self._population_tags.clear()
        self._population_outputs.clear()
