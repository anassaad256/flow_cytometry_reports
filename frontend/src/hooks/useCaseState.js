import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'fcr_currentCase'

const INITIAL_STATE = {
  specimen_type: '',
  clinical_data: '',
  adequacy_status: '',
  inadequate_reason: '',
  viability_percent: '',
  selected_panel_ids: [],
  panelData: {},  // { panel_id: { fields, regions: [{ region_id, fields, populations: [...] }] } }
}

function loadFromStorage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      // Merge with initial state to ensure all keys exist
      return { ...INITIAL_STATE, ...parsed }
    }
  } catch {
    // Ignore corrupt data
  }
  return null
}

function saveToStorage(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Ignore storage errors
  }
}

function clearStorage() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Ignore
  }
}

export function hasSavedCase() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      // Only consider it a saved case if at least specimen_type or adequacy is set
      return !!(parsed.specimen_type || parsed.adequacy_status)
    }
  } catch {
    // Ignore
  }
  return false
}

export default function useCaseState() {
  const [state, setState] = useState(INITIAL_STATE)
  const [initialized, setInitialized] = useState(false)

  // On mount, check for saved state
  useEffect(() => {
    const saved = loadFromStorage()
    if (saved) {
      setState(saved)
    }
    setInitialized(true)
  }, [])

  // Auto-save on every state change (after initial load)
  useEffect(() => {
    if (initialized) {
      saveToStorage(state)
    }
  }, [state, initialized])

  const updateField = useCallback((field, value) => {
    setState(prev => ({ ...prev, [field]: value }))
  }, [])

  const togglePanel = useCallback((panelId) => {
    setState(prev => {
      const ids = prev.selected_panel_ids.includes(panelId)
        ? prev.selected_panel_ids.filter(id => id !== panelId)
        : [...prev.selected_panel_ids, panelId]
      return { ...prev, selected_panel_ids: ids }
    })
  }, [])

  const setPanelData = useCallback((panelId, data) => {
    setState(prev => ({
      ...prev,
      panelData: { ...prev.panelData, [panelId]: data }
    }))
  }, [])

  const reset = useCallback(() => {
    clearStorage()
    setState(INITIAL_STATE)
  }, [])

  const buildCaseInput = useCallback(() => {
    const input = {
      specimen_type: state.specimen_type,
      clinical_data: state.clinical_data,
      adequacy_status: state.adequacy_status,
    }

    if (state.adequacy_status === 'ADEQUACY_INADEQUATE') {
      input.inadequate_reason = state.inadequate_reason
      if (state.inadequate_reason === 'INADEQUATE_LOW_VIABILITY' && state.viability_percent) {
        input.viability_percent = parseFloat(state.viability_percent)
      }
      input.selected_panels = []
    } else {
      if (state.viability_percent) {
        input.viability_percent = parseFloat(state.viability_percent)
      }
      input.selected_panels = state.selected_panel_ids.map(panelId => {
        const pd = state.panelData[panelId] || {}
        return {
          panel_id: panelId,
          fields: pd.fields || {},
          regions: (pd.regions || []).map(r => ({
            region_id: r.region_id,
            fields: r.fields || {},
            populations: (r.populations || []).map(p => ({
              population_id: p.population_id,
              fields: p.fields || {},
              marker_states: (p.marker_states || []).map(ms => ({
                marker_id: ms.marker_id,
                state: ms.state
              }))
            }))
          }))
        }
      })
    }
    return input
  }, [state])

  return { state, updateField, togglePanel, setPanelData, reset, buildCaseInput, initialized }
}
