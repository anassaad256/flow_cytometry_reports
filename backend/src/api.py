"""FastAPI application with REST endpoints."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .models import CaseInput, ReportOutput
from .report_generator import ReportGenerator

app = FastAPI(title="Flow Cytometry Report Generator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the report generator
_trees_dir = os.environ.get(
    "DECISION_TREES_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "decision_trees"),
)
generator = ReportGenerator(_trees_dir)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/generate", response_model=ReportOutput)
def generate_report(case_input: CaseInput):
    """Generate a flow cytometry report from structured case input."""
    try:
        return generator.generate(case_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/panels")
def get_panels():
    """Return available panels with metadata."""
    return generator.get_available_panels()


@app.get("/api/panel/{panel_id}/schema")
def get_panel_schema(panel_id: str):
    """Return the panel input schema for dynamic form generation."""
    schema = generator.get_panel_schema(panel_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Panel {panel_id} not found")
    return schema


@app.get("/api/enums")
def get_enums():
    """Return global enums for the UI."""
    return generator.get_global_enums()


# Serve frontend static files in production
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve frontend SPA — fallback to index.html for client-side routing."""
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")
