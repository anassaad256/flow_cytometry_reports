"""Tests for PanelRunner — integration tests with real YAML specs."""
from __future__ import annotations

import pytest

from src.context import EvaluationContext
from src.panel_runner import PanelRunner
from tests.conftest import make_marker_states


class TestPanelRunnerAcuteLeukemia:
    """Test PanelRunner with the acute leukemia panel spec."""

    @pytest.fixture
    def acute_spec(self, panel_registry):
        return panel_registry["PANEL_ACUTE_LEUKEMIA"]

    @pytest.fixture
    def runner(self, acute_spec, main_tree):
        ctx = EvaluationContext(main_tree)
        ctx.push_scope({})  # case scope placeholder
        return PanelRunner(acute_spec, ctx)

    def test_adequate_myeloblasts_produces_comment_lines(self, acute_spec, main_tree):
        """Verify the bug fix: comment_lines must be non-empty for adequate cases."""
        ctx = EvaluationContext(main_tree)
        ctx.push_scope({"adequacy_status": "ADEQUACY_ADEQUATE"})
        runner = PanelRunner(acute_spec, ctx)

        panel_input = {
            "panel_id": "PANEL_ACUTE_LEUKEMIA",
            "fields": {"cyto_tube_performed": "CYTO_TUBE_NO"},
            "regions": [
                {
                    "region_id": "REGION_BLASTS",
                    "fields": {},
                    "populations": [
                        {
                            "population_id": "POP_BLASTS",
                            "fields": {
                                "blast_type": "BLAST_MYELOBLASTS",
                                "pct_gated_events": 45.0,
                            },
                            "marker_states": make_marker_states({
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
                            }),
                        }
                    ],
                }
            ],
        }
        output = runner.run(panel_input)

        assert output.panel_id == "PANEL_ACUTE_LEUKEMIA"
        # Bug fix verification: comment_lines should NOT be empty
        assert len(output.comment_lines) > 0, "comment_lines should be populated for adequate cases"
        # Should mention myeloblasts somewhere in the comment
        comment_text = " ".join(output.comment_lines)
        assert "myeloblast" in comment_text.lower() or "45" in comment_text

    def test_adequate_myeloblasts_produces_main_line_items(self, acute_spec, main_tree):
        ctx = EvaluationContext(main_tree)
        ctx.push_scope({})
        runner = PanelRunner(acute_spec, ctx)

        panel_input = {
            "panel_id": "PANEL_ACUTE_LEUKEMIA",
            "fields": {"cyto_tube_performed": "CYTO_TUBE_NO"},
            "regions": [
                {
                    "region_id": "REGION_BLASTS",
                    "fields": {},
                    "populations": [
                        {
                            "population_id": "POP_BLASTS",
                            "fields": {
                                "blast_type": "BLAST_MYELOBLASTS",
                                "pct_gated_events": 20.0,
                            },
                            "marker_states": make_marker_states({
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
                            }),
                        }
                    ],
                }
            ],
        }
        output = runner.run(panel_input)
        assert len(output.main_line_items) > 0

    def test_antibody_markers_no_cyto(self, acute_spec, main_tree):
        """Cyto tube NO should use the no-cyto marker set."""
        ctx = EvaluationContext(main_tree)
        ctx.push_scope({})
        runner = PanelRunner(acute_spec, ctx)

        panel_input = {
            "panel_id": "PANEL_ACUTE_LEUKEMIA",
            "fields": {"cyto_tube_performed": "CYTO_TUBE_NO"},
            "regions": [],
        }
        output = runner.run(panel_input)
        markers = output.antibody_panel_markers
        # With no cyto, cyto-specific markers should not appear
        assert all(not m.startswith("M_CYTO_") for m in markers)

    def test_antibody_markers_with_cyto(self, acute_spec, main_tree):
        """Cyto tube YES should include cyto markers."""
        ctx = EvaluationContext(main_tree)
        ctx.push_scope({})
        runner = PanelRunner(acute_spec, ctx)

        panel_input = {
            "panel_id": "PANEL_ACUTE_LEUKEMIA",
            "fields": {"cyto_tube_performed": "CYTO_TUBE_YES"},
            "regions": [],
        }
        output = runner.run(panel_input)
        markers = output.antibody_panel_markers
        # With cyto, we should have cyto markers
        assert any(m.startswith("M_CYTO_") for m in markers)
