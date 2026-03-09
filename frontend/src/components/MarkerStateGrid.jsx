import React from 'react'

const MARKER_STATES = [
  { value: 'STATE_NA', label: 'N/A', color: '#e0e0e0', textColor: '#888' },
  { value: 'STATE_POSITIVE', label: 'Pos', color: '#4caf50', textColor: '#fff' },
  { value: 'STATE_NEGATIVE', label: 'Neg', color: '#f44336', textColor: '#fff' },
  { value: 'STATE_BRIGHT', label: 'Bright', color: '#ff9800', textColor: '#fff' },
  { value: 'STATE_DIM', label: 'Dim', color: '#9c27b0', textColor: '#fff' },
  { value: 'STATE_SUBSET', label: 'Sub', color: '#2196f3', textColor: '#fff' },
  { value: 'STATE_VARIABLE', label: 'Var', color: '#607d8b', textColor: '#fff' },
]

const stateIndex = Object.fromEntries(MARKER_STATES.map((s, i) => [s.value, i]))

export default function MarkerStateGrid({ markers, markerCatalog, markerStates, onChange }) {
  const handleClick = (markerId) => {
    const updated = markerStates.map(ms => {
      if (ms.marker_id !== markerId) return ms
      const idx = stateIndex[ms.state] ?? 0
      const nextIdx = (idx + 1) % MARKER_STATES.length
      return { ...ms, state: MARKER_STATES[nextIdx].value }
    })
    onChange(updated)
  }

  return (
    <div className="marker-grid">
      {markers.map(markerId => {
        const info = markerCatalog[markerId] || {}
        const display = info.display || markerId
        const currentState = markerStates.find(ms => ms.marker_id === markerId)?.state || 'STATE_NA'
        const stateInfo = MARKER_STATES[stateIndex[currentState]] || MARKER_STATES[0]

        return (
          <button
            key={markerId}
            type="button"
            className="marker-chip"
            onClick={() => handleClick(markerId)}
            style={{
              backgroundColor: stateInfo.color,
              color: stateInfo.textColor,
              border: 'none',
              borderRadius: '8px',
              padding: '8px 12px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              minWidth: '100px',
              textAlign: 'center',
              transition: 'background-color 0.15s',
            }}
            title={`${display}: ${stateInfo.label} (click to cycle)`}
          >
            {display}: {stateInfo.label}
          </button>
        )
      })}
    </div>
  )
}
