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

  // Determine active markers for this population based on panel-level fields
  const activeMarkers = getActiveMarkers(populationSpec, panelSchema)

  const updateField = (field, value) => {
    const newFields = { ...population.fields, [field]: value }

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

  // Track blast_type to detect changes
  const blastTypeRef = React.useRef(population.fields.blast_type)

  // Initialize marker states with defaults when markers first appear
  React.useEffect(() => {
    if (activeMarkers.length > 0 && population.marker_states.length === 0) {
      const initial = activeMarkers.map(m => ({
        marker_id: m,
        state: defaults[m] || 'STATE_NA'
      }))
      onChange({ ...population, marker_states: initial })
    }
  }, [activeMarkers.length])

  // Re-apply defaults when blast_type changes
  React.useEffect(() => {
    const currentBlastType = population.fields.blast_type
    if (currentBlastType && currentBlastType !== blastTypeRef.current && activeMarkers.length > 0) {
      blastTypeRef.current = currentBlastType
      const updated = activeMarkers.map(m => ({
        marker_id: m,
        state: defaults[m] || 'STATE_NA'
      }))
      onChange({ ...population, marker_states: updated })
    }
  }, [population.fields.blast_type, defaults, activeMarkers])

  // Determine which fields to show based on population type
  const requiredInputs = populationSpec?.inputs?.required || []
  const optionalInputs = populationSpec?.inputs?.optional || []

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

      {/* Render required/optional fields */}
      {[...requiredInputs, ...optionalInputs]
        .filter(f => f !== 'marker_states')
        .filter(f => {
          // Hide kappa_percent/lambda_percent for plasma cells unless polyclonal
          if ((f === 'kappa_percent' || f === 'lambda_percent') && popId === 'POP_PLASMA_CELLS') {
            return population.fields.pc_outcome === 'PC_POLYCLONAL'
          }
          return true
        })
        .map(field => renderField(field, population.fields[field], updateField, panelEnums))}

      {/* Marker state grid */}
      {activeMarkers.length > 0 && (
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
    .replace(/^(BLAST_|CYTO_TUBE_|PC_|FSC_|T_|PERFORMED_)/, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}
