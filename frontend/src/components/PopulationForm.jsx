import React from 'react'
import MarkerStateGrid from './MarkerStateGrid'

export default function PopulationForm({
  population,
  populationSpec,
  panelSchema,
  regionFields,
  index,
  onChange,
  onRemove,
  canRemove
}) {
  const popId = population.population_id
  const panelEnums = panelSchema.enums || {}
  const markerCatalog = panelSchema.marker_catalog || {}

  // Determine active markers — merge population fields so t_normality etc. are visible
  const schemaWithPopFields = React.useMemo(() => ({
    ...panelSchema,
    _currentFields: { ...(panelSchema._currentFields || {}), ...population.fields }
  }), [panelSchema, population.fields])
  const activeMarkers = getActiveMarkers(populationSpec, schemaWithPopFields)

  const updateField = (field, value) => {
    const newFields = { ...population.fields, [field]: value }

    // When b_outcome changes, reset dependent fields to avoid stale data
    if (field === 'b_outcome' && popId === 'POP_B_CELLS') {
      delete newFields.restricted_chain
      delete newFields.fsc_size
      delete newFields.kappa_percent
      delete newFields.lambda_percent
    }

    // Auto-calculate between pct_gated_events and pct_region using region_pct_total
    // Only auto-calc when value is a finalized number (not a string being typed)
    if (typeof value === 'number') {
      const regionPct = regionFields?.region_pct_total
      if (regionPct && parseFloat(regionPct) > 0) {
        const rp = parseFloat(regionPct)
        if (field === 'pct_gated_events') {
          newFields.pct_region = Math.round((value / rp) * 10000) / 100
        } else if (field === 'pct_region') {
          newFields.pct_gated_events = Math.round((value * rp) / 100 * 100) / 100
        }
      }
    }

    const updated = {
      ...population,
      fields: newFields
    }
    onChange(updated)
  }

  const updateMarkerStates = (newStates) => {
    onChange({ ...population, marker_states: newStates })
  }

  // Resolve default marker states from population spec
  const defaults = React.useMemo(() => {
    return resolveDefaultMarkerStates(populationSpec, population.fields)
  }, [populationSpec, population.fields])

  // Track blast_type to detect full-reset changes
  const blastTypeRef = React.useRef(population.fields.blast_type)

  // Reconcile marker states when active marker list changes (e.g. t_normality toggle,
  // panel marker options change). Keeps existing states for markers still in the list,
  // adds new markers with defaults, removes markers no longer active.
  const activeMarkersKey = activeMarkers.join(',')
  React.useEffect(() => {
    if (activeMarkers.length === 0) return

    // Full reset when blast_type changes (acute leukemia)
    const currentBlastType = population.fields.blast_type
    if (currentBlastType && currentBlastType !== blastTypeRef.current) {
      blastTypeRef.current = currentBlastType
      const updated = activeMarkers.map(m => ({
        marker_id: m,
        state: defaults[m] || 'STATE_NA'
      }))
      onChange({ ...population, marker_states: updated })
      return
    }
    blastTypeRef.current = currentBlastType

    // First-time initialization or reconciliation after marker list change
    const currentIds = new Set(population.marker_states.map(m => m.marker_id))
    const targetIds = new Set(activeMarkers)
    const needsReconcile = population.marker_states.length === 0 ||
      activeMarkers.some(m => !currentIds.has(m)) ||
      population.marker_states.some(m => !targetIds.has(m.marker_id))

    if (!needsReconcile) return

    const existingMap = {}
    population.marker_states.forEach(m => { existingMap[m.marker_id] = m.state })
    const reconciled = activeMarkers.map(m => ({
      marker_id: m,
      state: existingMap[m] || defaults[m] || 'STATE_NA'
    }))
    onChange({ ...population, marker_states: reconciled })
  }, [activeMarkersKey, population.fields.blast_type])

  // Determine which fields to show based on population type
  const requiredInputs = populationSpec?.inputs?.required || []
  const optionalInputs = populationSpec?.inputs?.optional || []

  // Build visible field list with conditional filtering
  const allFields = [...requiredInputs, ...optionalInputs].filter(f => f !== 'marker_states')
  const visibleFields = allFields
    .filter(f => isFieldVisible(f, popId, population.fields, allFields))

  // Sort fields so pct_gated_events and pct_region are adjacent
  const orderedFields = orderFields(visibleFields, popId)

  // Should we show the marker grid?
  const showMarkers = activeMarkers.length > 0 && shouldShowMarkers(popId, population.fields, allFields)

  return (
    <div className="population-entry">
      <div className="population-entry-header">
        <h4>{getPopulationLabel(popId)} #{index + 1}</h4>
        {canRemove && (
          <button className="btn btn-danger" style={{ padding: '4px 10px', fontSize: '0.8rem' }} onClick={onRemove}>
            Remove
          </button>
        )}
      </div>

      {/* Render fields with pct pairing */}
      {orderedFields.map(field => {
        // Skip pct_region if it will be paired with pct_gated_events
        if (field === 'pct_region' && orderedFields.includes('pct_gated_events')) return null
        // Pair pct_gated_events with pct_region side by side
        if (field === 'pct_gated_events' && orderedFields.includes('pct_region')) {
          return (
            <div key="pct-row" className="form-row">
              {renderField('pct_gated_events', population.fields.pct_gated_events, updateField, panelEnums)}
              {renderField('pct_region', population.fields.pct_region, updateField, panelEnums)}
            </div>
          )
        }
        return renderField(field, population.fields[field], updateField, panelEnums)
      })}

      {/* Marker state grid */}
      {showMarkers && (
        <div className="form-group">
          <label>Marker States</label>
          <MarkerStateGrid
            markers={activeMarkers}
            markerCatalog={markerCatalog}
            markerStates={population.marker_states}
            onChange={updateMarkerStates}
          />
        </div>
      )}
    </div>
  )
}

// Determine if the marker grid should be shown
function shouldShowMarkers(popId, fields, availableFields) {
  if (popId === 'POP_B_CELLS' && availableFields.includes('b_outcome')) {
    const outcome = fields.b_outcome
    return outcome === 'B_MONOCLONAL' || outcome === 'B_POLYCLONAL'
  }
  return true
}

// Determine if a field should be visible based on population state
function isFieldVisible(field, popId, fields, availableFields) {
  // Plasma cell conditional fields
  if (popId === 'POP_PLASMA_CELLS') {
    if (field === 'kappa_percent' || field === 'lambda_percent') {
      return fields.pc_outcome === 'PC_POLYCLONAL'
    }
    if (field === 'cd56_state') {
      const outcome = fields.pc_outcome
      return outcome && outcome !== 'PC_INSUFFICIENT'
    }
  }

  // B cell conditional fields — only apply when b_outcome is in the schema
  if (popId === 'POP_B_CELLS' && availableFields.includes('b_outcome')) {
    const bOutcome = fields.b_outcome
    if (!bOutcome) {
      // Before outcome is selected, only show b_outcome and pct fields
      if (field === 'restricted_chain' || field === 'fsc_size' || field === 'kappa_percent' || field === 'lambda_percent') return false
      return true
    }
    if (field === 'restricted_chain') return bOutcome === 'B_MONOCLONAL'
    if (field === 'fsc_size') return bOutcome === 'B_MONOCLONAL'
    if (field === 'kappa_percent' || field === 'lambda_percent') return bOutcome === 'B_POLYCLONAL'
    if (field === 'pct_gated_events' || field === 'pct_region') return bOutcome !== 'B_NONE'
  }

  return true
}

// Reorder fields so pct_gated_events and pct_region are adjacent, and
// key decision fields come first
function orderFields(fields, popId) {
  const preferredOrder = {
    POP_B_CELLS: ['b_outcome', 'pct_gated_events', 'pct_region', 'restricted_chain', 'fsc_size', 'kappa_percent', 'lambda_percent'],
    POP_T_CELLS: ['pct_gated_events', 'pct_region', 't_normality', 'cd4_percent', 'cd8_percent'],
    POP_TLGL: ['pct_gated_events', 'pct_region', 't_normality'],
  }
  const order = preferredOrder[popId]
  if (!order) return fields
  return [...fields].sort((a, b) => {
    const ai = order.indexOf(a)
    const bi = order.indexOf(b)
    if (ai === -1 && bi === -1) return 0
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
}


function getPopulationLabel(popId) {
  const labels = {
    POP_BLASTS: 'Blasts',
    POP_MONOCYTES: 'Monocytes',
    POP_PLASMA_CELLS: 'Plasma Cells',
    POP_B_CELLS: 'B Cells',
    POP_T_CELLS: 'T Cells',
    POP_TLGL: 'T-LGL',
  }
  return labels[popId] || popId
}

function getActiveMarkers(populationSpec, panelSchema) {
  const gen = populationSpec?.active_markers_generation?.templates || []
  const constants = panelSchema.constants || {}
  const panelFields = panelSchema._currentFields || {}

  // Sort templates by priority descending (highest priority first)
  const sorted = [...gen].sort((a, b) => (b.priority || 0) - (a.priority || 0))

  // Try to match predicates against panel-level fields
  for (const tmpl of sorted) {
    const when = tmpl.when
    if (when && matchesPredicate(when, panelFields)) {
      const ref = tmpl.markers_ref
      if (ref && constants[ref]) {
        return constants[ref]
      }
    }
  }

  // Fallback: use the first template's markers_ref
  for (const tmpl of sorted) {
    const ref = tmpl.markers_ref
    if (ref && constants[ref]) {
      return constants[ref]
    }
  }

  return []
}

function matchesPredicate(pred, fields) {
  if (pred.field_equals) {
    const { field, value } = pred.field_equals
    return fields[field] === value
  }
  if (pred.all) {
    return pred.all.every(p => matchesPredicate(p, fields))
  }
  if (pred.any) {
    return pred.any.some(p => matchesPredicate(p, fields))
  }
  if (pred.not) {
    return !matchesPredicate(pred.not, fields)
  }
  if (pred.default !== undefined) {
    return pred.default
  }
  return false
}

function resolveDefaultMarkerStates(populationSpec, populationFields) {
  const templates = populationSpec?.default_marker_states || []
  for (const tmpl of templates) {
    if (tmpl.when && matchesPredicate(tmpl.when, populationFields || {})) {
      const result = {}
      const states = tmpl.states || {}
      for (const [state, markers] of Object.entries(states)) {
        for (const m of markers) {
          result[m] = state
        }
      }
      return result
    }
  }
  return {}
}

function renderField(field, value, updateField, panelEnums) {
  // Detect enum fields
  const enumMap = {
    blast_type: 'blast_type',
    cyto_tube_performed: 'cyto_tube_status',
    pc_outcome: 'pc_outcome',
    fsc_size: 'fsc_size',
    t_normality: 't_normality',
    b_outcome: 'b_outcome',
    restricted_chain: 'b_restricted_chain',
    cd56_state: null, // marker state enum
    hairy_cell_markers_performed: 'performed_status',
    t_nk_markers_performed: 'performed_status',
  }

  const fieldLabels = {
    blast_type: 'Blast Type',
    pct_gated_events: '% of Gated Events',
    pct_all_viable: '% of All Viable',
    pct_region: '% of Region',
    pc_outcome: 'Plasma Cell Outcome',
    cd56_state: 'CD56 State',
    kappa_percent: 'Kappa %',
    lambda_percent: 'Lambda %',
    fsc_size: 'FSC Size',
    t_normality: 'T Cell Normality',
    b_outcome: 'B Cell Outcome',
    restricted_chain: 'Restricted Chain',
    cd4_percent: 'CD4 %',
    cd8_percent: 'CD8 %',
    region_pct_total: 'Region % Total',
    region_features_text: 'Region Features',
  }

  const label = fieldLabels[field] || field.replace(/_/g, ' ')

  // Check if it's a marker state (like cd56_state)
  if (field === 'cd56_state') {
    const states = [
      { value: 'STATE_POSITIVE', label: 'Positive' },
      { value: 'STATE_BRIGHT', label: 'Bright' },
      { value: 'STATE_NEGATIVE', label: 'Negative' },
      { value: 'STATE_SUBSET', label: 'Subset' },
      { value: 'STATE_DIM', label: 'Dim' },
      { value: 'STATE_VARIABLE', label: 'Variable' },
      { value: 'STATE_NA', label: 'N/A' },
    ]
    return (
      <div className="form-group" key={field}>
        <label>{label}</label>
        <select value={value || ''} onChange={e => updateField(field, e.target.value)}>
          <option value="">Select...</option>
          {states.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>
    )
  }

  if (enumMap[field] && panelEnums[enumMap[field]]) {
    const options = panelEnums[enumMap[field]]
    // Use radio-style buttons for short enum lists, select for longer ones
    if (options.length <= 5) {
      return (
        <div className="form-group" key={field}>
          <label>{label}</label>
          <div className="radio-group">
            {options.map(opt => (
              <div
                key={opt}
                className={`radio-option ${value === opt ? 'selected' : ''}`}
                onClick={() => updateField(field, opt)}
              >
                {formatEnumLabel(opt)}
              </div>
            ))}
          </div>
        </div>
      )
    }
    return (
      <div className="form-group" key={field}>
        <label>{label}</label>
        <select value={value || ''} onChange={e => updateField(field, e.target.value)}>
          <option value="">Select...</option>
          {options.map(opt => (
            <option key={opt} value={opt}>{formatEnumLabel(opt)}</option>
          ))}
        </select>
      </div>
    )
  }

  // Numeric fields
  if (field.includes('pct') || field.includes('percent') || field === 'region_pct_total') {
    return (
      <div className="form-group" key={field}>
        <label>{label}</label>
        <input
          type="number"
          step="0.01"
          min="0"
          max="100"
          value={value ?? ''}
          onChange={e => updateField(field, e.target.value === '' ? '' : e.target.value)}
          onBlur={e => { if (e.target.value !== '') updateField(field, parseFloat(e.target.value)) }}
          placeholder="0.00"
        />
      </div>
    )
  }

  // Text fields
  return (
    <div className="form-group" key={field}>
      <label>{label}</label>
      <input
        type="text"
        value={value || ''}
        onChange={e => updateField(field, e.target.value)}
      />
    </div>
  )
}

function formatEnumLabel(value) {
  return value
    .replace(/^(BLAST_|CYTO_TUBE_|PC_|FSC_|T_|PERFORMED_|B_)/, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}
