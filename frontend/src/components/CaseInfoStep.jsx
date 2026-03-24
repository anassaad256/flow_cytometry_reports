import React, { useState } from 'react'

const PRESET_SPECIMENS = ['Bone marrow', 'Blood', 'Lymph node']

export default function CaseInfoStep({ state, updateField }) {
  const isPreset = PRESET_SPECIMENS.includes(state.specimen_type)
  const [otherMode, setOtherMode] = useState(!isPreset && state.specimen_type !== '')

  const handleChoice = (choice) => {
    if (choice === 'Other') {
      if (otherMode) {
        setOtherMode(false)
        updateField('specimen_type', '')
      } else {
        setOtherMode(true)
        updateField('specimen_type', '')
      }
    } else {
      setOtherMode(false)
      updateField('specimen_type', state.specimen_type === choice ? '' : choice)
    }
  }

  return (
    <div className="card">
      <h2>Case Information</h2>
      <div className="form-group">
        <label>Specimen Type</label>
        <div className="radio-group">
          {PRESET_SPECIMENS.map(choice => (
            <div
              key={choice}
              className={`radio-option${state.specimen_type === choice ? ' selected' : ''}`}
              onClick={() => handleChoice(choice)}
            >
              {choice}
            </div>
          ))}
          <div
            className={`radio-option${otherMode ? ' selected' : ''}`}
            onClick={() => handleChoice('Other')}
          >
            Other
          </div>
        </div>
        {otherMode && (
          <input
            type="text"
            value={state.specimen_type}
            onChange={e => updateField('specimen_type', e.target.value)}
            placeholder="Specify specimen type"
            style={{ marginTop: '8px' }}
            autoFocus
          />
        )}
      </div>
      <div className="form-group">
        <label>Clinical Data <span style={{ fontWeight: 400, color: 'var(--on-surface-variant)' }}>(optional)</span></label>
        <textarea
          value={state.clinical_data}
          onChange={e => updateField('clinical_data', e.target.value)}
          placeholder="e.g., AML, status post chemotherapy"
        />
      </div>
    </div>
  )
}
