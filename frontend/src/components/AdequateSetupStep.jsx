import React from 'react'

export default function AdequateSetupStep({ state, updateField, togglePanel, panels, onNext, onBack }) {
  const canProceed = state.viability_percent && state.selected_panel_ids.length > 0

  return (
    <div className="card">
      <h2>Adequate Case Setup</h2>

      <div className="form-group">
        <label>Viability (%)</label>
        <input
          type="number"
          step="1"
          min="0"
          max="100"
          value={state.viability_percent}
          onChange={e => updateField('viability_percent', e.target.value)}
          placeholder="e.g., 85"
        />
      </div>

      <div className="form-group">
        <label>Select Panel(s)</label>
        <div className="panel-chips">
          {panels.map(p => (
            <div
              key={p.panel_id}
              className={`panel-chip ${state.selected_panel_ids.includes(p.panel_id) ? 'selected' : ''}`}
              onClick={() => togglePanel(p.panel_id)}
            >
              {p.name}
            </div>
          ))}
        </div>
      </div>

      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onBack}>Back</button>
        <button className="btn btn-primary" onClick={onNext} disabled={!canProceed}>
          Next
        </button>
      </div>
    </div>
  )
}
