> **Last updated: 2026-03-18 15:45 UTC**
>
> This document describes the project structure, architecture, and usage. It may fall out of date as the codebase evolves. Compare the date above with the most recent commit to determine if this document needs refreshing. When making significant changes to the project, update this file and the date accordingly.

# Flow Cytometry Clinical Report Generator

A deterministic clinical report generation system for flow cytometry analysis. Clinicians input structured case data through a step-by-step wizard, and the system produces standardized pathology consultation reports using a YAML-driven decision tree engine.

## Overview

This tool automates the generation of flow cytometry reports used in clinical pathology. It supports multiple diagnostic panels (Acute Leukemia, Lymphoproliferative/T-NK, Plasma Cell Myeloma, MDS) and produces three report sections:

- **General** — Header with specimen info, viability, antibody panel performed, and lab disclaimer
- **Main Line** — Diagnostic finding summary with priority-sorted findings
- **Comment** — Detailed immunophenotypic narrative per region/population

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend (React / Vite)                            │
│  Step-by-step wizard: Case Info → Adequacy →        │
│  Panel Selection → Region/Population Data → Report  │
└────────────────────┬────────────────────────────────┘
                     │ POST /api/generate
┌────────────────────▼────────────────────────────────┐
│  Backend (FastAPI / Python)                         │
│  ┌──────────────────────────────────────────────┐   │
│  │ ReportGenerator                              │   │
│  │  └─ MainTreeRunner (case-level orchestration)│   │
│  │      └─ PanelRunner (per-panel execution)    │   │
│  │          ├─ TagEngine (marker → tag mapping)  │   │
│  │          ├─ TemplateSelector (priority match) │   │
│  │          ├─ DerivedComputer (marker lists,    │   │
│  │          │   percentages, ratios)             │   │
│  │          ├─ TextRenderer ({var} interpolation)│   │
│  │          └─ Validators (input validation)     │   │
│  └──────────────────────────────────────────────┘   │
│                        ▲                            │
│  ┌─────────────────────┴────────────────────────┐   │
│  │ Decision Trees (YAML)                        │   │
│  │  Main-tree.txt    — global orchestration     │   │
│  │  acute_norm.yaml  — acute leukemia panel     │   │
│  │  lympro_tnk_norm.yaml — lymphoproliferative  │   │
│  │  plasma_norm.yaml — plasma cell myeloma      │   │
│  │  mds_norm.yaml    — MDS panel                │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` requests to `http://localhost:8000`.

### Run Tests

```bash
cd backend
python -m pytest tests/ -q
```

## Supported Panels

| Panel | ID | Regions | Key Features |
|---|---|---|---|
| Acute Leukemia | `PANEL_ACUTE_LEUKEMIA` | Blasts, Monocytes | Cyto tube gating, myeloblast/B/T lymphoblast classification, 20% AML threshold |
| Lymphoproliferative / T-NK | `PANEL_LYMPHOPROLIF_TLGL` | Lymphocytes | B cell restriction (kappa/lambda), T cell aberrancy, hairy cell add-on markers |
| Plasma Cell Myeloma | `PANEL_PLASMA_CELL_MYELOMA` | Plasma Cells | Outcome-driven (insufficient/polyclonal/kappa/lambda restricted), CD56 aberrancy |
| MDS | `PANEL_MDS` | Blasts, Monocytes | Simplified acute leukemia markers, no cyto tube |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/generate` | Generate report from `CaseInput` JSON |
| `GET` | `/api/panels` | List available panels |
| `GET` | `/api/panel/{panel_id}/schema` | Panel input schema for dynamic UI |
| `GET` | `/api/enums` | Global enum values |

## Project Structure

```
flow_cytometry_reports/
├── backend/
│   ├── src/
│   │   ├── api.py                 # FastAPI endpoints
│   │   ├── report_generator.py    # Top-level API: CaseInput → ReportOutput
│   │   ├── main_tree_runner.py    # Case-level orchestration
│   │   ├── panel_runner.py        # Per-panel execution engine
│   │   ├── context.py             # Hierarchical scoped context + tag store
│   │   ├── tag_engine.py          # Marker → tag computation + rule evaluation
│   │   ├── template_selector.py   # Priority-based template matching
│   │   ├── text_renderer.py       # {variable} interpolation + helper clauses
│   │   ├── derived.py             # Computed values (marker lists, percentages, ratios)
│   │   ├── predicates.py          # Predicate evaluators for the DSL
│   │   ├── transformers.py        # Marker dedup, display, sorting
│   │   ├── validators.py          # Validation rule engine
│   │   ├── panel_loader.py        # YAML loading + panel registry
│   │   └── models.py              # Pydantic input/output models
│   └── tests/                     # 71 tests covering all modules
├── decision_trees/
│   ├── Main-tree.txt              # Global orchestration + constants
│   ├── acute_norm.yaml            # Acute leukemia panel rules
│   ├── lympro_tnk_norm.yaml       # Lymphoproliferative / T-NK rules
│   ├── plasma_norm.yaml           # Plasma cell myeloma rules
│   └── mds_norm.yaml              # MDS panel rules
├── frontend/
│   └── src/
│       ├── App.jsx                # Main wizard flow
│       ├── api.js                 # Axios API client
│       ├── hooks/useCaseState.js  # Case state management with localStorage
│       └── components/
│           ├── CaseInfoStep.jsx       # Specimen type + clinical data
│           ├── AdequacyStep.jsx       # Adequate/Inadequate selection
│           ├── InadequateReasonStep.jsx
│           ├── AdequateSetupStep.jsx  # Viability + panel selection
│           ├── PanelWizard.jsx        # Per-panel region/population entry
│           ├── PopulationForm.jsx     # Population fields + marker grid
│           ├── MarkerStateGrid.jsx    # Marker state selection grid
│           ├── ReportOutput.jsx       # Final report display
│           └── WizardStepper.jsx      # Step indicator
└── render.yaml                    # Render.com deployment config
```

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, PyYAML
- **Frontend**: React 18, Vite, Axios
- **Testing**: pytest
- **Deployment**: Render.com (render.yaml)
