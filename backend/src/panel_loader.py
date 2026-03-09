"""YAML loading and panel registry construction."""
from __future__ import annotations

import os

import yaml


def load_yaml(filepath: str) -> dict:
    """Load a YAML file and return the parsed dict."""
    with open(filepath, "r") as f:
        return yaml.safe_load(f) or {}


def load_main_tree(decision_trees_dir: str) -> dict:
    """Load the main tree specification."""
    path = os.path.join(decision_trees_dir, "Main-tree.txt")
    return load_yaml(path)


def build_panel_registry(main_tree: dict, decision_trees_dir: str) -> dict[str, dict]:
    """Build a registry mapping panel_id -> loaded panel spec.

    Uses the main tree's panel_registry to find panel pack references,
    then scans the decision_trees directory for matching YAML files.
    """
    registry: dict[str, dict] = {}

    # Scan all yaml files in the directory
    panel_files: list[str] = []
    for fname in os.listdir(decision_trees_dir):
        if fname.endswith((".yaml", ".yml")):
            panel_files.append(os.path.join(decision_trees_dir, fname))

    # Load each panel file and register by panel_id
    for filepath in panel_files:
        try:
            spec = load_yaml(filepath)
        except Exception:
            continue
        panel_section = spec.get("panel", {})
        panel_id = panel_section.get("panel_id")
        if panel_id:
            registry[panel_id] = spec

    return registry
