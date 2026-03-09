import React from 'react'

export default function WizardStepper({ steps, currentStep, isInadequate, onStepClick }) {
  const visibleSteps = isInadequate
    ? steps.filter(s => s.id !== 'panels')
    : steps

  return (
    <div className="stepper">
      {visibleSteps.map((s, idx) => {
        const realIdx = steps.indexOf(s)
        let cls = 'stepper-step'
        const isCompleted = realIdx < currentStep
        if (isCompleted) cls += ' completed'
        else if (realIdx === currentStep) cls += ' active'
        return (
          <div
            key={s.id}
            className={cls}
            style={isCompleted ? { cursor: 'pointer' } : {}}
            onClick={() => isCompleted && onStepClick && onStepClick(realIdx)}
          >
            <span>{idx + 1}</span>
            <span>{s.label}</span>
          </div>
        )
      })}
    </div>
  )
}
