"""Shared fixtures for flow cytometry report tests."""
from __future__ import annotations

import os
import pytest

from src.context import EvaluationContext
from src.panel_loader import build_panel_registry, load_main_tree
from src.report_generator import ReportGenerator


DECISION_TREES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "decision_trees",
)


@pytest.fixture(scope="session")
def decision_trees_dir():
    return DECISION_TREES_DIR


@pytest.fixture(scope="session")
def main_tree(decision_trees_dir):
    return load_main_tree(decision_trees_dir)


@pytest.fixture(scope="session")
def panel_registry(main_tree, decision_trees_dir):
    return build_panel_registry(main_tree, decision_trees_dir)


@pytest.fixture(scope="session")
def generator(decision_trees_dir):
    return ReportGenerator(decision_trees_dir)


@pytest.fixture
def ctx(main_tree):
    """Fresh EvaluationContext for each test."""
    return EvaluationContext(main_tree)


def make_marker_states(states_dict: dict[str, str]) -> list[dict]:
    """Helper: {'M_CD14': 'STATE_POSITIVE', ...} -> [{'marker_id': ..., 'state': ...}]"""
    return [{"marker_id": k, "state": v} for k, v in states_dict.items()]


def make_adequate_acute_input(
    blast_type: str = "BLAST_MYELOBLASTS",
    cyto_tube: str = "CYTO_TUBE_NO",
    pct_blasts: float = 45.0,
    marker_states: dict[str, str] | None = None,
) -> dict:
    """Build a CaseInput dict for an adequate acute leukemia case."""
    if marker_states is None:
        marker_states = {
            "M_CD14": "STATE_NEGATIVE",
            "M_CD13": "STATE_POSITIVE",
            "M_CD33": "STATE_POSITIVE",
            "M_CD117": "STATE_POSITIVE",
            "M_CD34": "STATE_POSITIVE",
            "M_HLA_DR": "STATE_POSITIVE",
            "M_CD11B": "STATE_NEGATIVE",
            "M_CD16": "STATE_NEGATIVE",
            "M_CD56": "STATE_NEGATIVE",
            "M_CD7": "STATE_NEGATIVE",
            "M_CD19": "STATE_NEGATIVE",
            "M_CD10": "STATE_NEGATIVE",
            "M_CD64": "STATE_NEGATIVE",
            "M_CD15": "STATE_NEGATIVE",
            "M_CD38": "STATE_POSITIVE",
            "M_CD123": "STATE_NEGATIVE",
            "M_CD4": "STATE_NEGATIVE",
            "M_CD36": "STATE_NEGATIVE",
        }
    return {
        "specimen_type": "Bone marrow aspirate",
        "clinical_data": "AML workup",
        "adequacy_status": "ADEQUACY_ADEQUATE",
        "viability_percent": 92.0,
        "selected_panels": [
            {
                "panel_id": "PANEL_ACUTE_LEUKEMIA",
                "fields": {"cyto_tube_performed": cyto_tube},
                "regions": [
                    {
                        "region_id": "REGION_BLASTS",
                        "fields": {},
                        "populations": [
                            {
                                "population_id": "POP_BLASTS",
                                "fields": {
                                    "blast_type": blast_type,
                                    "pct_gated_events": pct_blasts,
                                },
                                "marker_states": make_marker_states(marker_states),
                            }
                        ],
                    }
                ],
            }
        ],
    }
