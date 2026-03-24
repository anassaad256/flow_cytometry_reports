import React, { useState, useEffect } from 'react'
import { fetchPanelSchema } from '../api'
import PopulationForm from './PopulationForm'

const PANEL_LABELS = {
  PANEL_ACUTE_LEUKEMIA: 'Acute Leukemia',
  PANEL_MDS: 'MDS',
  PANEL_PLASMA_CELL_MYELOMA: 'Plasma Cell Myeloma',
  PANEL_LYMPHOPROLIF_TLGL: 'Lymphoproliferative / T NK',
}

const REGION_LABELS = {
  REGION_BLASTS: 'Blasts',
  REGION_MONOCYTES: 'Monocytes',
  REGION_PLASMA_CELLS: 'Plasma Cells',
  REGION_LYMPHOCYTES: 'Lymphocytes',
}

export default function PanelWizard({ state, setPanelData, onGenerate, loading }) {
  const [schemas, setSchemas] = useState({})
  const [activePanelIdx, setActivePanelIdx] = useState(0)
  const [loadingSchemas, setLoadingSchemas] = useState(true)

  const selectedPanels = state.selected_panel_ids || []

  // Load schemas for all selected panels
  useEffect(() => {
    let cancelled = false
    setLoadingSchemas(true)
    Promise.all(selectedPanels.map(pid => fetchPanelSchema(pid)))
      .then(results => {
        if (cancelled) return
        const map = {}
        results.forEach((schema, i) => { map[selectedPanels[i]] = schema })
        setSchemas(map)
        setLoadingSchemas(false)
      })
      .catch(() => setLoadingSchemas(false))
    return () => { cancelled = true }
  }, [selectedPanels.join(',')])

  if (loadingSchemas) {
    return <div className="loading">Loading panel schemas...</div>
  }

  const currentPanelId = selectedPanels[activePanelIdx]
  const schema = schemas[currentPanelId]

  if (!schema) {
    return <div className="card"><p>No schema available for panel.</p></div>
  }

  const panelData = state.panelData[currentPanelId] || { fields: {}, regions: [] }

  const updatePanelData = (newData) => {
    setPanelData(currentPanelId, newData)
  }

  const isLastPanel = activePanelIdx === selectedPanels.length - 1
  const isFirstPanel = activePanelIdx === 0

  const handlePanelNext = () => {
    if (isLastPanel) {
      onGenerate()
    } else {
      setActivePanelIdx(i => i + 1)
    }
  }

  const handlePanelBack = () => {
    if (!isFirstPanel) {
      setActivePanelIdx(i => i - 1)
    }
  }

  return (
    <div>
      {/* Panel tabs */}
      {selectedPanels.length > 1 && (
        <div className="stepper" style={{ marginBottom: 16 }}>
          {selectedPanels.map((pid, i) => (
            <div
              key={pid}
              className={`stepper-step ${i === activePanelIdx ? 'active' : i < activePanelIdx ? 'completed' : ''}`}
              onClick={() => setActivePanelIdx(i)}
              style={{ cursor: 'pointer' }}
            >
              {PANEL_LABELS[pid] || pid}
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2>{PANEL_LABELS[currentPanelId] || currentPanelId}</h2>

        {/* Panel-level inputs */}
        <PanelLevelInputs
          schema={schema}
          panelData={panelData}
          onChange={updatePanelData}
        />

        {/* Regions and populations */}
        <RegionsEditor
          schema={schema}
          panelData={panelData}
          onChange={updatePanelData}
        />

        <div className="btn-row" style={{ justifyContent: 'flex-end' }}>
          {!isFirstPanel && (
            <button className="btn btn-secondary" onClick={handlePanelBack}>
              Previous Panel
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handlePanelNext}
            disabled={loading}
          >
            {loading ? 'Generating...' : isLastPanel ? 'Generate Report' : 'Next Panel'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Panel-level inputs (e.g., cyto_tube_performed, hairy_cell_markers_performed)
function PanelLevelInputs({ schema, panelData, onChange }) {
  const required = schema.panel_inputs?.required || []
  const optional = schema.panel_inputs?.optional || []
  const allInputs = [...required, ...optional]
  const panelEnums = schema.enums || {}

  if (allInputs.length === 0) return null

  const updateField = (field, value) => {
    onChange({ ...panelData, fields: { ...panelData.fields, [field]: value } })
  }

  return (
    <div style={{ marginBottom: 20 }}>
      <h3>Panel Settings</h3>
      {allInputs.map(field => (
        <PanelField
          key={field}
          field={field}
          value={panelData.fields[field] || ''}
          onChange={updateField}
          panelEnums={panelEnums}
        />
      ))}
    </div>
  )
}

function PanelField({ field, value, onChange, panelEnums }) {
  const enumMap = {
    cyto_tube_performed: 'cyto_tube_status',
    hairy_cell_markers_performed: 'performed_status',
    t_nk_markers_performed: 'performed_status',
  }
  const labelMap = {
    cyto_tube_performed: 'Cyto Tube Performed?',
    hairy_cell_markers_performed: 'Hairy Cell Markers Performed?',
    t_nk_markers_performed: 'T/NK Markers Performed?',
  }

  const label = labelMap[field] || field.replace(/_/g, ' ')
  const enumKey = enumMap[field]

  if (enumKey && panelEnums[enumKey]) {
    const options = panelEnums[enumKey]
    return (
      <div className="form-group">
        <label>{label}</label>
        <div className="radio-group">
          {options.map(opt => (
            <div
              key={opt}
              className={`radio-option ${value === opt ? 'selected' : ''}`}
              onClick={() => onChange(field, opt)}
            >
              {formatEnumLabel(opt)}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="form-group">
      <label>{label}</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(field, e.target.value)}
      />
    </div>
  )
}

// Regions editor: handles adding/removing populations within regions
function RegionsEditor({ schema, panelData, onChange }) {
  const regions = schema.regions || []

  // Build a flat list of population specs for reference
  const populationSpecs = {}
  regions.forEach(r => {
    (r.populations || []).forEach(p => {
      populationSpecs[`${r.region_id}:${p.population_id}`] = { ...p, region_id: r.region_id }
    })
  })

  // Get current regions from panelData
  const currentRegions = panelData.regions || []

  // For single-region panels (like plasma, lymphoproliferative), flatten the UX
  const isSingleRegion = regions.length === 1
  const singleRegion = isSingleRegion ? regions[0] : null

  // Get region-level input fields
  const getRegionInputs = (regionSpec) => {
    const required = regionSpec?.inputs?.required || []
    const optional = regionSpec?.inputs?.optional || []
    return [...required, ...optional]
  }

  // Find or create region data
  const getRegionData = (regionId) => {
    return currentRegions.find(r => r.region_id === regionId) || {
      region_id: regionId,
      fields: {},
      populations: [],
    }
  }

  const updateRegionData = (regionId, newRegionData) => {
    const existing = currentRegions.find(r => r.region_id === regionId)
    let updated
    if (existing) {
      updated = currentRegions.map(r => r.region_id === regionId ? newRegionData : r)
    } else {
      updated = [...currentRegions, newRegionData]
    }
    onChange({ ...panelData, regions: updated })
  }

  const addPopulation = (regionId, populationId) => {
    const region = getRegionData(regionId)
    const newPop = { population_id: populationId, fields: {}, marker_states: [] }
    const updatedRegion = {
      ...region,
      populations: [...region.populations, newPop],
    }
    updateRegionData(regionId, updatedRegion)
  }

  const removePopulation = (regionId, popIndex) => {
    const region = getRegionData(regionId)
    const updatedRegion = {
      ...region,
      populations: region.populations.filter((_, i) => i !== popIndex),
    }
    updateRegionData(regionId, updatedRegion)
  }

  const updatePopulation = (regionId, popIndex, newPop) => {
    const region = getRegionData(regionId)
    const updatedRegion = {
      ...region,
      populations: region.populations.map((p, i) => i === popIndex ? newPop : p),
    }
    updateRegionData(regionId, updatedRegion)
  }

  const updateRegionField = (regionId, field, value) => {
    const region = getRegionData(regionId)
    updateRegionData(regionId, {
      ...region,
      fields: { ...region.fields, [field]: value },
    })
  }

  return (
    <div>
      {regions.map(regionSpec => {
        const regionId = regionSpec.region_id
        const regionData = getRegionData(regionId)
        const regionInputFields = getRegionInputs(regionSpec)
        const popSpecs = regionSpec.populations || []

        return (
          <div key={regionId} style={{ marginBottom: 24 }}>
            {!isSingleRegion && (
              <h3>{REGION_LABELS[regionId] || regionId} Region</h3>
            )}

            {/* Region-level fields */}
            {regionInputFields.map(field => (
              <RegionField
                key={field}
                field={field}
                value={regionData.fields[field] || ''}
                onChange={(f, v) => updateRegionField(regionId, f, v)}
              />
            ))}

            {/* Add population buttons */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
              {popSpecs.map(ps => (
                <button
                  key={ps.population_id}
                  className="add-population-btn"
                  style={{ width: 'auto', flex: '0 0 auto', padding: '8px 16px' }}
                  onClick={() => addPopulation(regionId, ps.population_id)}
                >
                  + Add {getPopLabel(ps.population_id)}
                </button>
              ))}
            </div>

            {/* Population forms */}
            {regionData.populations.map((pop, idx) => {
              const popSpec = popSpecs.find(ps => ps.population_id === pop.population_id)
              if (!popSpec) return null

              // Merge panel-level fields into schema for active marker resolution
              const schemaWithFields = {
                ...schema,
                _currentFields: panelData.fields || {},
              }

              return (
                <PopulationForm
                  key={`${pop.population_id}-${idx}`}
                  population={pop}
                  populationSpec={popSpec}
                  panelSchema={schemaWithFields}
                  regionFields={regionData.fields || {}}
                  index={idx}
                  onChange={(newPop) => updatePopulation(regionId, idx, newPop)}
                  onRemove={() => removePopulation(regionId, idx)}
                  canRemove={true}
                />
              )
            })}

            {regionData.populations.length === 0 && (
              <p style={{ color: 'var(--on-surface-variant)', fontSize: '14px', fontStyle: 'italic' }}>
                No populations added yet. Click a button above to add one.
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}

function RegionField({ field, value, onChange }) {
  const labelMap = {
    region_pct_total: 'Region % Total',
    region_features_text: 'Region Features',
  }
  const label = labelMap[field] || field.replace(/_/g, ' ')

  if (field.includes('pct') || field.includes('percent')) {
    return (
      <div className="form-group">
        <label>{label} (optional)</label>
        <input
          type="number"
          step="0.01"
          min="0"
          max="100"
          value={value ?? ''}
          onChange={e => onChange(field, e.target.value === '' ? '' : e.target.value)}
          onBlur={e => { if (e.target.value !== '') onChange(field, parseFloat(e.target.value)) }}
          placeholder="0.00"
        />
      </div>
    )
  }

  return (
    <div className="form-group">
      <label>{label} (optional)</label>
      <input
        type="text"
        value={value}
        onChange={e => onChange(field, e.target.value)}
      />
    </div>
  )
}

function getPopLabel(popId) {
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

function formatEnumLabel(value) {
  return value
    .replace(/^(BLAST_|CYTO_TUBE_|PC_|FSC_|T_|PERFORMED_|INADEQUATE_)/, '')
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())
}
