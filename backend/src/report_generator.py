"""Top-level API: CaseInput -> ReportOutput."""
from __future__ import annotations

import os

from .main_tree_runner import MainTreeRunner
from .models import CaseInput, ReportOutput
from .panel_loader import build_panel_registry, load_main_tree


class ReportGenerator:
    """Initialize once with decision tree specs, then call generate() for each case."""

    def __init__(self, decision_trees_dir: str | None = None):
        if decision_trees_dir is None:
            # Default: look for decision_trees relative to project root
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            decision_trees_dir = os.path.join(base, "decision_trees")

        self.main_tree = load_main_tree(decision_trees_dir)
        self.panel_registry = build_panel_registry(self.main_tree, decision_trees_dir)

    def generate(self, case_input: CaseInput) -> ReportOutput:
        runner = MainTreeRunner(self.main_tree, self.panel_registry)
        return runner.run(case_input)

    def get_available_panels(self) -> list[dict]:
        """Return metadata about available panels for the UI."""
        panels = []
        for panel_id, spec in self.panel_registry.items():
            panel_section = spec.get("panel", {})
            ids_section = spec.get("ids", {})
            panel_names = ids_section.get("panels", {})
            name = panel_names.get(panel_id, panel_id)
            panels.append({
                "panel_id": panel_id,
                "name": name,
                "has_inputs": bool(panel_section.get("inputs", {}).get("required")),
            })
        return panels

    def get_panel_schema(self, panel_id: str) -> dict | None:
        """Return the panel input schema for dynamic form generation."""
        spec = self.panel_registry.get(panel_id)
        if not spec:
            return None

        panel_section = spec.get("panel", {})
        result: dict = {
            "panel_id": panel_id,
            "panel_inputs": panel_section.get("inputs", {}),
            "enums": spec.get("enums", {}),
            "marker_catalog": spec.get("marker_catalog", {}),
            "regions": [],
        }

        for region_spec in panel_section.get("regions", []):
            region_info: dict = {
                "region_id": region_spec.get("region_id", ""),
                "inputs": region_spec.get("inputs", {}),
                "populations": [],
            }
            for pop_spec in region_spec.get("populations", []):
                pop_info = {
                    "population_id": pop_spec.get("population_id", ""),
                    "allow_multiple": pop_spec.get("allow_multiple", False),
                    "toggle_only": pop_spec.get("toggle_only", False),
                    "inputs": pop_spec.get("inputs", {}),
                    "active_markers_generation": pop_spec.get("active_markers_generation", {}),
                    "default_marker_states": pop_spec.get("default_marker_states", []),
                }
                region_info["populations"].append(pop_info)
            result["regions"].append(region_info)

        # Include constants needed for marker resolution
        result["constants"] = spec.get("constants", {})

        return result

    def get_global_enums(self) -> dict:
        """Return global enums for the UI."""
        return {
            "marker_states": [
                {"value": "STATE_POSITIVE", "label": "Positive"},
                {"value": "STATE_BRIGHT", "label": "Bright"},
                {"value": "STATE_NEGATIVE", "label": "Negative"},
                {"value": "STATE_SUBSET", "label": "Subset"},
                {"value": "STATE_DIM", "label": "Dim"},
                {"value": "STATE_VARIABLE", "label": "Variable"},
                {"value": "STATE_NA", "label": "N/A"},
            ],
            "adequacy_status": [
                {"value": "ADEQUACY_ADEQUATE", "label": "Adequate"},
                {"value": "ADEQUACY_INADEQUATE", "label": "Inadequate"},
            ],
            "inadequate_reasons": [
                {"value": "INADEQUATE_LOW_CELLULAR_EVENTS", "label": "Low cellular events"},
                {"value": "INADEQUATE_VISCOUS_SPECIMEN", "label": "Viscous specimen"},
                {"value": "INADEQUATE_LOW_VIABILITY", "label": "Low viability"},
            ],
        }
