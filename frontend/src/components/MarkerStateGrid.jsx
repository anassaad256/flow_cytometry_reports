import React from 'react'

const MARKER_STATES = [
  { value: 'STATE_POSITIVE', label: 'Pos' },
  { value: 'STATE_BRIGHT', label: 'Bright' },
  { value: 'STATE_NEGATIVE', label: 'Neg' },
  { value: 'STATE_SUBSET', label: 'Sub' },
  { value: 'STATE_DIM', label: 'Dim' },
  { value: 'STATE_VARIABLE', label: 'Var' },
  { value: 'STATE_NA', label: 'N/A' },
]

export default function MarkerStateGrid({ markers, markerCatalog, markerStates, onChange }) {
  const handleChange = (markerId, newState) => {
    const updated = markerStates.map(ms =>
      ms.marker_id === markerId ? { ...ms, state: newState } : ms
    )
    onChange(updated)
  }

  return (
    <div className="marker-grid">
      {markers.map(markerId => {
        const info = markerCatalog[markerId] || {}
        const display = info.display || markerId
        const currentState = markerStates.find(ms => ms.marker_id === markerId)?.state || 'STATE_NA'

        return (
          <div key={markerId} className="marker-item">
            <label>{display}</label>
            <select
              value={currentState}
              onChange={e => handleChange(markerId, e.target.value)}
            >
              {MARKER_STATES.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        )
      })}
    </div>
  )
}
