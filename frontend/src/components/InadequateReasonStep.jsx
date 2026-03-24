import React from 'react'

const REASONS = [
  { value: 'INADEQUATE_LOW_CELLULAR_EVENTS', label: 'Low cellular events' },
  { value: 'INADEQUATE_VISCOUS_SPECIMEN', label: 'Viscous specimen' },
  { value: 'INADEQUATE_LOW_VIABILITY', label: 'Low viability' },
]

export default function InadequateReasonStep({ state, updateField, onGenerate, loading }) {
  const showViability = state.inadequate_reason === 'INADEQUATE_LOW_VIABILITY'
  const canGenerate = state.inadequate_reason && (!showViability || state.viability_percent)

  return (
    <div className="card">
      <h2>Inadequate Reason</h2>
      <div className="form-group">
        <label>Select the reason for inadequacy</label>
        <div className="radio-group">
          {REASONS.map(r => (
            <div
              key={r.value}
              className={`radio-option ${state.inadequate_reason === r.value ? 'selected' : ''}`}
              onClick={() => updateField('inadequate_reason', r.value)}
            >
              {r.label}
            </div>
          ))}
        </div>
      </div>

      {showViability && (
        <div className="form-group">
          <label>Viability (%)</label>
          <input
            type="number"
            step="0.1"
            min="0"
            max="100"
            value={state.viability_percent}
            onChange={e => updateField('viability_percent', e.target.value)}
            placeholder="e.g., 15.0"
          />
        </div>
      )}

      <div className="btn-row" style={{ justifyContent: 'flex-end' }}>
        <button
          className="btn btn-primary"
          onClick={onGenerate}
          disabled={!canGenerate || loading}
        >
          {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>
    </div>
  )
}
