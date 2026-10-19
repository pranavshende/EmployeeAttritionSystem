import React from 'react';
import { Activity, Sparkles, UploadCloud, RotateCcw, FileSpreadsheet } from 'lucide-react';

export default function Header({
  datasetInfo = {},
  onOpenUploadModal,
  onResetDataset,
}) {
  const hasDataset = Boolean(datasetInfo && datasetInfo.has_dataset);
  const totalEmployees = (datasetInfo.total_employees || 0).toLocaleString();
  const datasetName = datasetInfo.dataset_name || 'No Dataset';

  return (
    <header className="dashboard-header">
      <div className="header-left">
        <div className="header-logo">
          <Activity size={26} strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="header-title">
            Employee Attrition <span className="header-title-highlight">Intelligence</span>
          </h1>
          <p className="header-subtitle">
            Dynamic CSV Synthesizer, Retention Diagnostics & Gemini AI Copilot
          </p>
        </div>
      </div>

      <div className="header-right" style={{ flexWrap: 'wrap', gap: '10px' }}>
        {/* Active Dataset Pill */}
        {hasDataset ? (
          <div
            className="status-badge green"
            title={`Active file: ${datasetName}`}
            style={{ maxWidth: '280px' }}
          >
            <span className="dot-pulse"></span>
            <FileSpreadsheet size={13} style={{ flexShrink: 0 }} />
            <span
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {datasetName} ({totalEmployees} records)
            </span>
          </div>
        ) : (
          <div
            className="status-badge"
            title="Awaiting CSV upload"
            style={{
              background: '#f8fafc',
              borderColor: '#e2e8f0',
              color: '#64748b',
            }}
          >
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#94a3b8',
                display: 'inline-block',
              }}
            ></span>
            <FileSpreadsheet size={13} />
            <span>Awaiting CSV Upload</span>
          </div>
        )}

        {/* Clear Dataset / New CSV Button (visible when a dataset is active) */}
        {hasDataset && (
          <button
            onClick={onResetDataset}
            title="Clear dataset and return to upload screen"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              background: '#ffffff',
              border: '1px solid #fecaca',
              borderRadius: 'var(--radius-full)',
              color: '#dc2626',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <RotateCcw size={13} />
            <span>Clear / New CSV</span>
          </button>
        )}

        {/* Upload Dataset Button */}
        <button
          onClick={onOpenUploadModal}
          title="Upload employee CSV file"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 16px',
            background: 'var(--gradient-primary)',
            border: 'none',
            borderRadius: 'var(--radius-full)',
            color: '#ffffff',
            fontSize: '0.78rem',
            fontWeight: 700,
            cursor: 'pointer',
            boxShadow: '0 3px 10px rgba(16, 185, 129, 0.3)',
            transition: 'all 0.2s ease',
          }}
        >
          <UploadCloud size={15} />
          <span>{hasDataset ? 'Upload Different CSV' : 'Upload CSV'}</span>
        </button>

        {/* Gemini Badge */}
        <div
          className="status-badge accent"
          style={{ borderColor: 'var(--primary-300)', color: 'var(--primary-700)' }}
        >
          <Sparkles size={14} style={{ color: 'var(--primary-500)' }} />
          <span>Gemini AI Connected</span>
        </div>
      </div>
    </header>
  );
}
