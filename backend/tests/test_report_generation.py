"""End-to-end tests for report generation."""
from __future__ import annotations

import pytest

from src.models import CaseInput
from tests.conftest import make_adequate_acute_input


class TestAdequateReport:
    """Test full report generation for adequate cases."""

    def test_adequate_myeloblasts_full_report(self, generator):
        """End-to-end: adequate acute leukemia with myeloblasts."""
        case_dict = make_adequate_acute_input(
            blast_type="BLAST_MYELOBLASTS",
            pct_blasts=45.0,
        )
        case = CaseInput(**case_dict)
        report = generator.generate(case)

        # General section
        assert len(report.general) >= 3
        assert "Clinical Pathology Consultation Report" in report.general[0]
        assert "Bone marrow aspirate" in report.general[1]
        # Should have viability and antibody panel lines
        viability_lines = [l for l in report.general if "Viability" in l]
        assert len(viability_lines) >= 1
        antibody_lines = [l for l in report.general if "Antibody Panel" in l]
        assert len(antibody_lines) >= 1

        # Main line section
        assert len(report.main_line) >= 2
        assert "flow cytometry analysis" in report.main_line[0].lower()

        # Comment section — the key bug fix verification
        assert len(report.comment) > 0, "Comment lines must be populated for adequate cases"

    def test_adequate_b_lymphoblasts(self, generator):
        case_dict = make_adequate_acute_input(blast_type="BLAST_B_LYMPHOBLASTS")
        case = CaseInput(**case_dict)
        report = generator.generate(case)
        assert len(report.comment) > 0

    def test_adequate_with_cyto_tube(self, generator):
        case_dict = make_adequate_acute_input(cyto_tube="CYTO_TUBE_YES")
        # Add cyto markers
        case_dict["selected_panels"][0]["regions"][0]["populations"][0]["marker_states"].extend([
            {"marker_id": "M_CYTO_CD3", "state": "STATE_NEGATIVE"},
            {"marker_id": "M_CYTO_CD79A", "state": "STATE_NEGATIVE"},
            {"marker_id": "M_CYTO_MPO", "state": "STATE_POSITIVE"},
            {"marker_id": "M_CYTO_TDT", "state": "STATE_NEGATIVE"},
        ])
        case = CaseInput(**case_dict)
        report = generator.generate(case)
        assert len(report.comment) > 0
        # Antibody panel should mention cyto markers
        antibody_line = [l for l in report.general if "Antibody Panel" in l]
        if antibody_line:
            assert "cyto" in antibody_line[0].lower() or "Cyto" in antibody_line[0]

    def test_low_viability_caution(self, generator):
        """Low viability should add a caution comment."""
        case_dict = make_adequate_acute_input()
        case_dict["viability_percent"] = 30.0
        case = CaseInput(**case_dict)
        report = generator.generate(case)
        caution_lines = [l for l in report.comment if "caution" in l.lower()]
        assert len(caution_lines) >= 1


class TestInadequateReport:
    """Test report generation for inadequate cases."""

    def test_inadequate_low_cellular_events(self, generator):
        case = CaseInput(
            specimen_type="Bone marrow aspirate",
            clinical_data="Pancytopenia",
            adequacy_status="ADEQUACY_INADEQUATE",
            inadequate_reason="INADEQUATE_LOW_CELLULAR_EVENTS",
        )
        report = generator.generate(case)
        assert len(report.main_line) >= 1
        main_text = " ".join(report.main_line)
        assert "low cellular events" in main_text.lower() or "could not be performed" in main_text.lower()
        # Comment should be empty for this inadequate type
        assert len(report.comment) == 0

    def test_inadequate_viscous_specimen(self, generator):
        case = CaseInput(
            specimen_type="Bone marrow aspirate",
            clinical_data="Pancytopenia",
            adequacy_status="ADEQUACY_INADEQUATE",
            inadequate_reason="INADEQUATE_VISCOUS_SPECIMEN",
        )
        report = generator.generate(case)
        assert len(report.main_line) >= 1
        assert len(report.comment) >= 1
        assert report.comment[0] == "Comment:"
        assert "viscous" in report.comment[1].lower()

    def test_inadequate_low_viability(self, generator):
        case = CaseInput(
            specimen_type="Peripheral blood",
            clinical_data="Leukemia",
            adequacy_status="ADEQUACY_INADEQUATE",
            inadequate_reason="INADEQUATE_LOW_VIABILITY",
            viability_percent=15.0,
        )
        report = generator.generate(case)
        main_text = " ".join(report.main_line)
        assert "viability" in main_text.lower() or "15" in main_text


class TestAvailablePanels:
    """Test panel metadata endpoints."""

    def test_get_available_panels(self, generator):
        panels = generator.get_available_panels()
        assert len(panels) >= 1
        panel_ids = {p["panel_id"] for p in panels}
        assert "PANEL_ACUTE_LEUKEMIA" in panel_ids

    def test_get_panel_schema(self, generator):
        schema = generator.get_panel_schema("PANEL_ACUTE_LEUKEMIA")
        assert schema is not None
        assert schema["panel_id"] == "PANEL_ACUTE_LEUKEMIA"
        assert "regions" in schema
        assert len(schema["regions"]) >= 1

    def test_get_panel_schema_not_found(self, generator):
        assert generator.get_panel_schema("NONEXISTENT") is None

    def test_get_global_enums(self, generator):
        enums = generator.get_global_enums()
        assert "marker_states" in enums
        assert "adequacy_status" in enums
        assert len(enums["marker_states"]) == 7
