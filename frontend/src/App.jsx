import React, { useState, useEffect } from 'react'
import { fetchPanels, fetchEnums, generateReport } from './api'
import useCaseState, { hasSavedCase } from './hooks/useCaseState'
import WizardStepper from './components/WizardStepper'
import CaseInfoStep from './components/CaseInfoStep'
import AdequacyStep from './components/AdequacyStep'
import InadequateReasonStep from './components/InadequateReasonStep'
import AdequateSetupStep from './components/AdequateSetupStep'
import PanelWizard from './components/PanelWizard'
import ReportOutput from './components/ReportOutput'

const STEPS = [
  { id: 'case_info', label: 'Case Info' },
  { id: 'adequacy', label: 'Adequacy' },
  { id: 'details', label: 'Details' },
  { id: 'panels', label: 'Panel Data' },
  { id: 'report', label: 'Report' },
]

export default function App() {
  const [step, setStep] = useState(0)
  const [panels, setPanels] = useState([])
  const [enums, setEnums] = useState({})
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showRecovery, setShowRecovery] = useState(false)
  const caseState = useCaseState()

  useEffect(() => {
    Promise.all([fetchPanels(), fetchEnums()])
      .then(([p, e]) => { setPanels(p); setEnums(e) })
      .catch(() => setError('Failed to connect to the backend server.'))
  }, [])

  // Show recovery prompt on first load if saved data exists
  useEffect(() => {
    if (caseState.initialized && hasSavedCase()) {
      setShowRecovery(true)
    }
  }, [caseState.initialized])

  const goNext = () => setStep(s => Math.min(s + 1, STEPS.length - 1))
  const goBack = () => setStep(s => Math.max(s - 1, 0))

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    try {
      const input = caseState.buildCaseInput()
      const result = await generateReport(input)
      setReport(result)
      setStep(STEPS.length - 1)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report')
    } finally {
      setLoading(false)
    }
  }

  const handleNewCase = () => {
    caseState.reset()
    setReport(null)
    setStep(0)
  }

  const handleEdit = () => {
    setReport(null)
    const isInadeq = caseState.state.adequacy_status === 'ADEQUACY_INADEQUATE'
    setStep(isInadeq ? 2 : 3)
  }

  const handleResumeCase = () => {
    setShowRecovery(false)
  }

  const handleDiscardCase = () => {
    setShowRecovery(false)
    caseState.reset()
  }

  const isInadequate = caseState.state.adequacy_status === 'ADEQUACY_INADEQUATE'

  // Recovery prompt
  if (showRecovery) {
    return (
      <div className="app">
        <header className="app-header">
          <h1>Flow Cytometry Report Generator</h1>
          <p>Deterministic clinical report generation from structured inputs</p>
        </header>
        <div className="card">
          <h2>Resume Previous Case?</h2>
          <p style={{ marginBottom: 16, color: '#636e72' }}>
            A previous case was found in your browser. Would you like to resume it or start fresh?
          </p>
          <div className="btn-row">
            <button className="btn btn-primary" onClick={handleResumeCase}>
              Resume Case
            </button>
            <button className="btn btn-secondary" onClick={handleDiscardCase}>
              Start New Case
            </button>
          </div>
        </div>
      </div>
    )
  }

  const renderStep = () => {
    switch (STEPS[step]?.id) {
      case 'case_info':
        return (
          <CaseInfoStep
            state={caseState.state}
            updateField={caseState.updateField}
            onNext={goNext}
          />
        )
      case 'adequacy':
        return (
          <AdequacyStep
            state={caseState.state}
            updateField={caseState.updateField}
            onNext={goNext}
            onBack={goBack}
          />
        )
      case 'details':
        if (isInadequate) {
          return (
            <InadequateReasonStep
              state={caseState.state}
              updateField={caseState.updateField}
              enums={enums}
              onGenerate={handleGenerate}
              onBack={goBack}
              loading={loading}
            />
          )
        }
        return (
          <AdequateSetupStep
            state={caseState.state}
            updateField={caseState.updateField}
            togglePanel={caseState.togglePanel}
            panels={panels}
            onNext={goNext}
            onBack={goBack}
          />
        )
      case 'panels':
        if (isInadequate) {
          handleGenerate()
          return <div className="loading">Generating report...</div>
        }
        return (
          <PanelWizard
            state={caseState.state}
            setPanelData={caseState.setPanelData}
            onGenerate={handleGenerate}
            onBack={goBack}
            loading={loading}
          />
        )
      case 'report':
        return (
          <ReportOutput
            report={report}
            onNewCase={handleNewCase}
            onEdit={handleEdit}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Flow Cytometry Report Generator</h1>
        <p>Deterministic clinical report generation from structured inputs</p>
      </header>

      <WizardStepper
        steps={STEPS}
        currentStep={step}
        isInadequate={isInadequate}
        onStepClick={(idx) => { if (idx < step) setStep(idx) }}
      />

      {error && (
        <div className="card" style={{ borderLeft: '4px solid #d63031' }}>
          <p style={{ color: '#d63031' }}>{error}</p>
        </div>
      )}

      {renderStep()}
    </div>
  )
}
