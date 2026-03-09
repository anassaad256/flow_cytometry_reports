import React from 'react'

const OPTIONS = [
  { value: 'ADEQUACY_ADEQUATE', label: 'Adequate' },
  { value: 'ADEQUACY_INADEQUATE', label: 'Inadequate' },
]

export default function AdequacyStep({ state, updateField, onNext, onBack }) {
  return (
    <div className="card">
      <h2>Specimen Adequacy</h2>
      <div className="form-group">
        <label>Is the specimen adequate for flow cytometry?</label>
        <div className="radio-group">
          {OPTIONS.map(opt => (
            <label
              key={opt.value}
              className={`radio-option ${state.adequacy_status === opt.value ? 'selected' : ''}`}
            >
              <input
                type="radio"
                name="adequacy"
                value={opt.value}
                checked={state.adequacy_status === opt.value}
                onChange={() => updateField('adequacy_status', opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>
      <div className="btn-row">
        <button className="btn btn-secondary" onClick={onBack}>Back</button>
        <button className="btn btn-primary" onClick={onNext} disabled={!state.adequacy_status}>
          Next
        </button>
      </div>
    </div>
  )
}
