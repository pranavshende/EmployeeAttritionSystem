import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, X, Sparkles } from 'lucide-react';
import { uploadDataset } from '../api';

const SAMPLE_CSV = `EmployeeID,Age,Department,JobRole,Salary,OverTime,YearsAtCompany,Attrition
101,23,Engineering,Frontend Engineer,4500,Yes,1,Yes
102,34,Marketing,Product Marketing Manager,7800,No,4,No
103,22,Engineering,Junior QA Engineer,3600,Yes,1,Yes
104,45,Finance,Financial Analyst,9400,No,8,No
105,29,Engineering,DevOps Specialist,6900,Yes,2,No
106,24,Marketing,Content Specialist,4100,Yes,1,Yes
107,38,Finance,Accounting Controller,11200,No,6,No
108,27,Engineering,Backend Engineer,6000,No,3,No
109,25,Sales,Account Executive,4800,Yes,1,Yes
110,32,Sales,Sales Director,9800,No,5,No
111,21,Customer Support,Support Associate,3200,Yes,1,Yes
112,41,Engineering,Principal Architect,14500,No,9,No
113,26,Customer Support,Support Lead,4900,No,2,No
114,35,Human Resources,HR Business Partner,7200,No,4,No
115,23,Sales,SDR Representative,3800,Yes,1,Yes
`;

export default function UploadModal({ isOpen, onClose, onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    setErrorMessage('');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  };

  const handleFileChange = (e) => {
    setErrorMessage('');
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      validateAndSetFile(file);
    }
  };

  const validateAndSetFile = (file) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setErrorMessage('Please upload a valid CSV file (.csv).');
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return;
    setIsUploading(true);
    setErrorMessage('');

    try {
      const result = await uploadDataset(selectedFile);
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
      onClose();
    } catch (err) {
      console.error('Upload failed:', err);
      setErrorMessage(err.message || 'Failed to upload and parse CSV.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUseSample = async () => {
    if (isUploading) return;
    setIsUploading(true);
    setErrorMessage('');

    try {
      const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
      const sampleFile = new File([blob], 'tech_startup_q3_cohort.csv', { type: 'text/csv' });
      const result = await uploadDataset(sampleFile);
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
      onClose();
    } catch (err) {
      console.error('Sample upload failed:', err);
      setErrorMessage(err.message || 'Failed to load sample dataset.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.45)',
        backdropFilter: 'blur(4px)',
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        animation: 'fadeIn 0.2s ease',
      }}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: 'var(--radius-xl)',
          width: '100%',
          maxWidth: '540px',
          boxShadow: 'var(--shadow-lg), 0 0 30px rgba(16, 185, 129, 0.15)',
          border: '1px solid var(--border-card)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'var(--gradient-header)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--primary-50)',
                color: 'var(--primary-700)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <UploadCloud size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)' }}>
                Ingest Dataset & Generate Dashboard
              </h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Upload any CSV — AI will synthesize KPIs, charts & chatbot intelligence
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '4px',
            }}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '24px' }}>
          {/* Dropzone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? 'var(--primary-500)' : 'var(--primary-200)'}`,
              background: isDragging ? 'var(--primary-50)' : 'var(--bg-page)',
              borderRadius: 'var(--radius-lg)',
              padding: '36px 20px',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".csv"
              style={{ display: 'none' }}
            />
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '50%',
                background: 'var(--primary-100)',
                color: 'var(--primary-600)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 12px',
              }}
            >
              <UploadCloud size={26} />
            </div>
            <p style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '4px' }}>
              Drag & drop your CSV file here, or <span style={{ color: 'var(--primary-600)' }}>browse</span>
            </p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Supports employee data with Department, Role, Salary, Attrition, Tenure, etc.
            </p>
          </div>

          {/* Selected File Badge */}
          {selectedFile && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                marginTop: '16px',
                padding: '12px 16px',
                background: 'var(--primary-50)',
                border: '1px solid var(--primary-200)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <FileText size={20} style={{ color: 'var(--primary-600)', flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {selectedFile.name}
                </p>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                  {(selectedFile.size / 1024).toFixed(1)} KB • CSV Format
                </p>
              </div>
              <CheckCircle2 size={18} style={{ color: 'var(--primary-600)', flexShrink: 0 }} />
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '16px',
                padding: '10px 14px',
                background: 'var(--danger-bg)',
                border: '1px solid var(--danger-border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--danger-text)',
                fontSize: '0.8rem',
              }}
            >
              <AlertCircle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Upload Progress Indicator */}
          {isUploading && (
            <div
              style={{
                marginTop: '16px',
                padding: '14px',
                background: 'var(--primary-50)',
                border: '1px solid var(--primary-200)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <Loader2 size={20} className="animate-spin" style={{ color: 'var(--primary-600)' }} />
              <div>
                <p style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--primary-800)' }}>
                  Analyzing CSV & Generating AI Intelligence...
                </p>
                <p style={{ fontSize: '0.72rem', color: 'var(--primary-700)' }}>
                  Calculating KPIs, charts, and tuning the Gemini chatbot to your dataset.
                </p>
              </div>
            </div>
          )}

          {/* Sample Demo Helper */}
          <div
            style={{
              marginTop: '20px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Don't have a CSV handy?
            </span>
            <button
              onClick={handleUseSample}
              disabled={isUploading}
              style={{
                background: '#ffffff',
                border: '1px solid var(--primary-300)',
                color: 'var(--primary-700)',
                padding: '6px 12px',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <Sparkles size={12} />
              <span>Load 15-Employee Sample Cohort</span>
            </button>
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '12px',
            padding: '16px 24px',
            background: 'var(--bg-page)',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <button
            onClick={onClose}
            disabled={isUploading}
            style={{
              background: '#ffffff',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              padding: '8px 16px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
            style={{
              background: !selectedFile || isUploading ? 'var(--text-muted)' : 'var(--gradient-primary)',
              border: 'none',
              color: '#ffffff',
              padding: '8px 20px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: !selectedFile || isUploading ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: !selectedFile || isUploading ? 'none' : '0 4px 12px rgba(16, 185, 129, 0.3)',
            }}
          >
            {isUploading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Sparkles size={14} />
                <span>Generate Dashboard with AI</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
