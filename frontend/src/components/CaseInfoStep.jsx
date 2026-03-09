import React from 'react'

const SPECIMEN_CHOICES = ['Bone marrow', 'Blood', 'Lymph node', 'Other']

export default function CaseInfoStep({ state, updateField, onNext }) {
  const specimenSelected = state.specimen_type.trim() !== ''
  const canProceed = specimenSelected

  // Determine which choice is active
  const isPreset = SPECIMEN_CHOICES.slice(0, -1).includes(state.specimen_type)
  const isOther = specimenSelected && !isPreset

  const handleChoice = (choice) => {
    if (choice === 'Other') {
      updateField('specimen_type', isOther ? '' : ' ')
    } else {
      updateField('specimen_type', state.specimen_type === choice ? '' : choice)
    }
  }

  return (
    <div className="card">
      <h2>Case Information</h2>
      <div className="form-group">
        <label>Specimen Type</label>
        <div className="radio-group">
          {SPECIMEN_CHOICES.map(choice => (
            <div
              key={choice}
              className={`radio-option${
                choice === 'Other'
                  ? isOther ? ' selected' : ''
                  : state.specimen_type === choice ? ' selected' : ''
              }`}
              onClick={() => handleChoice(choice)}
            >
              {choice}
            </div>
          ))}
        </div>
        {isOther && (
          <input
            type="text"
            value={state.specimen_type.trim()}
            onChange={e => updateField('specimen_type', e.target.value || ' ')}
            placeholder="Specify specimen type"
            style={{ marginTop: '8px' }}
            autoFocus
          />
        )}
      </div>
      <div className="form-group">
        <label>Clinical Data <span style={{ fontWeight: 400, color: '#999' }}>(optional)</span></label>
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
