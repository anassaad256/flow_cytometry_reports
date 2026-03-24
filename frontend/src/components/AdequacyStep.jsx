import React from 'react'

const OPTIONS = [
  { value: 'ADEQUACY_ADEQUATE', label: 'Adequate' },
  { value: 'ADEQUACY_INADEQUATE', label: 'Inadequate' },
]

export default function AdequacyStep({ state, updateField }) {
  return (
    <div className="card">
      <h2>Specimen Adequacy</h2>
      <div className="form-group">
        <label>Is the specimen adequate for flow cytometry?</label>
        <div className="radio-group">
          {OPTIONS.map(opt => (
            <div
              key={opt.value}
              className={`radio-option ${state.adequacy_status === opt.value ? 'selected' : ''}`}
              onClick={() => updateField('adequacy_status', opt.value)}
            >
              {opt.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
