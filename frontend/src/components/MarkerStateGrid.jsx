import React from 'react'

const STATES = [
  { value: 'STATE_POSITIVE', label: 'Pos' },
  { value: 'STATE_BRIGHT', label: 'Bright' },
  { value: 'STATE_DIM', label: 'Dim' },
  { value: 'STATE_NEGATIVE', label: 'Neg' },
  { value: 'STATE_SUBSET', label: 'Sub' },
  { value: 'STATE_VARIABLE', label: 'Var' },
]

export default function MarkerStateGrid({ markers, markerCatalog, markerStates, onChange }) {
  const handleToggle = (markerId, stateValue) => {
    const updated = markerStates.map(ms => {
      if (ms.marker_id !== markerId) return ms
      // If already selected, toggle back to N/A
      const newState = ms.state === stateValue ? 'STATE_NA' : stateValue
      return { ...ms, state: newState }
    })
    onChange(updated)
  }

  return (
    <div className="marker-state-table">
      <div className="marker-state-header">
        <div className="marker-name-col">Marker</div>
        {STATES.map(s => (
          <div key={s.value} className="marker-check-col">{s.label}</div>
        ))}
      </div>
      {markers.map(markerId => {
        const info = markerCatalog[markerId] || {}
        const display = info.display || markerId
        const currentState = markerStates.find(ms => ms.marker_id === markerId)?.state || 'STATE_NA'

        return (
          <div key={markerId} className="marker-state-row">
            <div className="marker-name-col">{display}</div>
            {STATES.map(s => (
              <div key={s.value} className="marker-check-col">
                <input
                  type="checkbox"
                  checked={currentState === s.value}
                  onChange={() => handleToggle(markerId, s.value)}
                />
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
