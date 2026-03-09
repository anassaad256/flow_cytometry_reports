"""Data models for flow cytometry report generator."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Global Enums ──────────────────────────────────────────────────────────────

class MarkerState(str, Enum):
    POSITIVE = "STATE_POSITIVE"
    BRIGHT = "STATE_BRIGHT"
    NEGATIVE = "STATE_NEGATIVE"
    SUBSET = "STATE_SUBSET"
    DIM = "STATE_DIM"
    VARIABLE = "STATE_VARIABLE"
    NA = "STATE_NA"


class AdequacyStatus(str, Enum):
    ADEQUATE = "ADEQUACY_ADEQUATE"
    INADEQUATE = "ADEQUACY_INADEQUATE"


class InadequateReason(str, Enum):
    LOW_CELLULAR_EVENTS = "INADEQUATE_LOW_CELLULAR_EVENTS"
    VISCOUS_SPECIMEN = "INADEQUATE_VISCOUS_SPECIMEN"
    LOW_VIABILITY = "INADEQUATE_LOW_VIABILITY"


class BlastType(str, Enum):
    MYELOBLASTS = "BLAST_MYELOBLASTS"
    B_LYMPHOBLASTS = "BLAST_B_LYMPHOBLASTS"
    T_LYMPHOBLASTS = "BLAST_T_LYMPHOBLASTS"


class CytoTubeStatus(str, Enum):
    NO = "CYTO_TUBE_NO"
    YES = "CYTO_TUBE_YES"


class PCOutcome(str, Enum):
    INSUFFICIENT = "PC_INSUFFICIENT"
    POLYCLONAL = "PC_POLYCLONAL"
    KAPPA_RESTRICTED = "PC_KAPPA_RESTRICTED"
    LAMBDA_RESTRICTED = "PC_LAMBDA_RESTRICTED"


class FSCSize(str, Enum):
    SMALL_TO_INTERMEDIATE = "FSC_SMALL_TO_INTERMEDIATE"
    INTERMEDIATE_TO_LARGE = "FSC_INTERMEDIATE_TO_LARGE"
    NA = "FSC_NA"


class TNormality(str, Enum):
    NORMAL = "T_NORMAL"
    ABNORMAL = "T_ABNORMAL"


class PerformedStatus(str, Enum):
    NO = "PERFORMED_NO"
    YES = "PERFORMED_YES"


# ── Expressed states constant ─────────────────────────────────────────────────

EXPRESSED_STATES = {
    MarkerState.POSITIVE,
    MarkerState.BRIGHT,
    MarkerState.SUBSET,
    MarkerState.DIM,
    MarkerState.VARIABLE,
}

MARKER_STATE_SUFFIX = {
    MarkerState.BRIGHT: "bright",
    MarkerState.DIM: "dim",
    MarkerState.SUBSET: "subset",
    MarkerState.VARIABLE: "variable",
}


# ── Input Models ──────────────────────────────────────────────────────────────

class MarkerStateInput(BaseModel):
    marker_id: str
    state: str  # Raw string like "STATE_POSITIVE"


class PopulationInput(BaseModel):
    population_id: str
    fields: dict[str, Any] = Field(default_factory=dict)
    marker_states: list[MarkerStateInput] = Field(default_factory=list)


class RegionInput(BaseModel):
    region_id: str
    fields: dict[str, Any] = Field(default_factory=dict)
    populations: list[PopulationInput] = Field(default_factory=list)


class PanelInput(BaseModel):
    panel_id: str
    fields: dict[str, Any] = Field(default_factory=dict)
    regions: list[RegionInput] = Field(default_factory=list)


class CaseInput(BaseModel):
    specimen_type: str
    clinical_data: str = ""
    adequacy_status: str  # "ADEQUACY_ADEQUATE" or "ADEQUACY_INADEQUATE"
    inadequate_reason: Optional[str] = None
    viability_percent: Optional[float] = None
    selected_panels: list[PanelInput] = Field(default_factory=list)


# ── Output Models ─────────────────────────────────────────────────────────────

class MainLineItem(BaseModel):
    text: str
    finding_priority: int = 750
    finding_class: str = "PANEL_NEGATIVE"
    panel_id: Optional[str] = None
    population_id: Optional[str] = None
    selection_order: int = 0


class ValidationResult(BaseModel):
    id: str
    severity: str  # "ERROR" or "WARN"
    message: str


class PanelOutput(BaseModel):
    panel_id: str
    antibody_panel_markers: list[str] = Field(default_factory=list)
    comment_lines: list[str] = Field(default_factory=list)
    main_line_items: list[MainLineItem] = Field(default_factory=list)


class ReportOutput(BaseModel):
    general: list[str] = Field(default_factory=list)
    main_line: list[str] = Field(default_factory=list)
    comment: list[str] = Field(default_factory=list)
    validation_errors: list[ValidationResult] = Field(default_factory=list)
