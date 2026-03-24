import React, { useState, useEffect, useRef } from 'react'
import { fetchPanels, fetchEnums, generateReport } from './api'
import useCaseState, { hasSavedCase } from './hooks/useCaseState'
import CaseInfoStep from './components/CaseInfoStep'
import AdequacyStep from './components/AdequacyStep'
import InadequateReasonStep from './components/InadequateReasonStep'
import AdequateSetupStep from './components/AdequateSetupStep'
import PanelWizard from './components/PanelWizard'
import ReportOutput from './components/ReportOutput'

export default function App() {
  const [panels, setPanels] = useState([])
  const [enums, setEnums] = useState({})
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showRecovery, setShowRecovery] = useState(false)
  const caseState = useCaseState()
  const reportRef = useRef(null)

  useEffect(() => {
    Promise.all([fetchPanels(), fetchEnums()])
      .then(([p, e]) => { setPanels(p); setEnums(e) })
      .catch(() => setError('Failed to connect to the backend server.'))
  }, [])

  useEffect(() => {
    if (caseState.initialized && hasSavedCase()) {
      setShowRecovery(true)
    }
  }, [caseState.initialized])

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const input = caseState.buildCaseInput()
      const result = await generateReport(input)
      setReport(result)
      setTimeout(() => reportRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report')
    } finally {
      setLoading(false)
    }
  }

  const handleNewCase = () => {
    caseState.reset()
    setReport(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleResumeCase = () => {
    setShowRecovery(false)
  }

  const handleDiscardCase = () => {
    setShowRecovery(false)
    caseState.reset()
  }

  const isInadequate = caseState.state.adequacy_status === 'ADEQUACY_INADEQUATE'
  const hasAdequacy = !!caseState.state.adequacy_status
  const hasSpecimen = caseState.state.specimen_type.trim() !== ''

  // Progressive disclosure
  const showAdequacy = hasSpecimen
  const showDetails = hasAdequacy
  const showPanels = !isInadequate && caseState.state.selected_panel_ids.length > 0 && caseState.state.viability_percent

  // Recovery prompt
  if (showRecovery) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Flow Cytometry Report Generator</h1>
        </header>
        <div className="resume-prompt">
          <div className="resume-card">
            <h2>Welcome Back</h2>
            <p>A previous case was found in your browser. Would you like to resume or start fresh?</p>
            <div className="resume-actions">
              <button className="btn btn-primary" onClick={handleResumeCase}>
                Resume Case
              </button>
              <button className="btn btn-secondary" onClick={handleDiscardCase}>
                Start New Case
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Flow Cytometry Report Generator</h1>
      </header>

      <div className="app-content">
        {error && (
          <div className="error-banner">{error}</div>
        )}

        {/* Step 1: Case Info — always visible */}
        <CaseInfoStep
          state={caseState.state}
          updateField={caseState.updateField}
        />

        {/* Step 2: Adequacy — appears after specimen chosen */}
        {showAdequacy && (
          <AdequacyStep
            state={caseState.state}
            updateField={caseState.updateField}
          />
        )}

        {/* Step 3: Details — appears after adequacy chosen */}
        {showDetails && (
          <>
            {isInadequate ? (
              <InadequateReasonStep
                state={caseState.state}
                updateField={caseState.updateField}
                enums={enums}
                onGenerate={handleGenerate}
                loading={loading}
              />
            ) : (
              <AdequateSetupStep
                state={caseState.state}
                updateField={caseState.updateField}
                togglePanel={caseState.togglePanel}
                panels={panels}
              />
            )}
          </>
        )}

        {/* Step 4: Panel Data — appears after panels selected */}
        {showPanels && (
          <PanelWizard
            state={caseState.state}
            setPanelData={caseState.setPanelData}
            onGenerate={handleGenerate}
            loading={loading}
          />
        )}

        {/* Report Output */}
        <div ref={reportRef}>
          {report && (
            <ReportOutput
              report={report}
              onNewCase={handleNewCase}
            />
          )}
        </div>
      </div>
    </div>
  )
}
