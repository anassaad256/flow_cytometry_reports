import React, { useState } from 'react'

export default function ReportOutput({ report, onNewCase }) {
  if (!report) {
    return null
  }

  const { general, main_line, comment, validation_errors } = report

  return (
    <div className="report-preview-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0 }}>Generated Report</h2>
        <button className="btn btn-secondary" onClick={onNewCase}>
          New Case
        </button>
      </div>

      <ReportSection title="General" lines={general} />
      <ReportSection title="Main Line" lines={main_line} />
      <ReportSection title="Comment" lines={comment} />

      {validation_errors && validation_errors.length > 0 && (
        <div className="report-section">
          <h3>Validation</h3>
          <div className="validation-errors">
            {validation_errors.map((err, i) => (
              <div key={i} className={`validation-error ${err.severity}`}>
                <strong>{err.severity}:</strong> {err.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {(!validation_errors || validation_errors.length === 0) && (
        <div className="report-section">
          <h3>Validation</h3>
          <p style={{ color: 'var(--success)', fontSize: '14px', fontWeight: 500 }}>No validation errors</p>
        </div>
      )}
    </div>
  )
}

function ReportSection({ title, lines }) {
  const [copied, setCopied] = useState(false)

  const text = (lines || []).join('\n')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (!lines || lines.length === 0) return null

  return (
    <div className="report-section">
      <h3>
        {title}
        <button className={`copy-btn${copied ? ' copied' : ''}`} onClick={handleCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </h3>
      <div className="report-text">{text}</div>
    </div>
  )
}
