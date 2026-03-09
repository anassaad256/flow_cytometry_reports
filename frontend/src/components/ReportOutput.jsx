import React, { useState } from 'react'

export default function ReportOutput({ report, onNewCase, onEdit }) {
  if (!report) {
    return (
      <div className="card">
        <p style={{ color: '#636e72' }}>No report generated yet.</p>
      </div>
    )
  }

  const { general, main_line, comment, validation_errors } = report

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>Generated Report</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            {onEdit && (
              <button className="btn btn-secondary" onClick={onEdit}>
                Edit
              </button>
            )}
            <button className="btn btn-primary" onClick={onNewCase}>
              New Case
            </button>
          </div>
        </div>

        <ReportSection title="General" lines={general} />
        <ReportSection title="Main Line" lines={main_line} />
        <ReportSection title="Comment" lines={comment} />

        {/* Validation messages */}
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
            <p style={{ color: '#00b894', fontSize: '0.9rem' }}>No validation errors</p>
          </div>
        )}
      </div>
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
      // Fallback for non-secure contexts
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
        <button className="copy-btn" onClick={handleCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </h3>
      <div className="report-text">{text}</div>
    </div>
  )
}
