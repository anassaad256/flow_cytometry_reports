import React from 'react'

export default function CaseInfoStep({ state, updateField, onNext }) {
  const canProceed = state.specimen_type.trim() && state.clinical_data.trim()

  return (
    <div className="card">
      <h2>Case Information</h2>
      <div className="form-group">
        <label>Specimen Type</label>
        <input
          type="text"
          value={state.specimen_type}
          onChange={e => updateField('specimen_type', e.target.value)}
          placeholder="e.g., Bone marrow aspirate, Peripheral blood"
        />
      </div>
      <div className="form-group">
        <label>Clinical Data</label>
        <textarea
          value={state.clinical_data}
          onChange={e => updateField('clinical_data', e.target.value)}
          placeholder="e.g., AML, status post chemotherapy"
        />
      </div>
      <div className="btn-row">
        <button className="btn btn-primary" onClick={onNext} disabled={!canProceed}>
          Next
        </button>
      </div>
    </div>
  )
}
