import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  Sparkles,
  BarChart3,
  ShieldAlert,
  BrainCircuit,
  Zap,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { uploadDataset, loadSampleDataset } from '../api';

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

export default function UploadHero({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

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
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    setErrorMessage('');
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (file) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setErrorMessage('Please upload a valid CSV file (.csv).');
      return;
    }

    try {
      setIsUploading(true);
      setUploadStatus(`Uploading & analyzing ${file.name}...`);
      const result = await uploadDataset(file);
      setUploadStatus('Generating AI insights & visualizations...');
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setErrorMessage(err.message || 'Failed to process CSV file. Please ensure it has valid columns.');
      setIsUploading(false);
    }
  };

  const handleSampleUpload = async () => {
    try {
      setIsUploading(true);
      setUploadStatus('Loading sample tech cohort dataset (15 employees)...');
      const blob = new Blob([SAMPLE_CSV], { type: 'text/csv' });
      const sampleFile = new File([blob], 'tech_startup_q3_cohort.csv', { type: 'text/csv' });
      const result = await uploadDataset(sampleFile);
      setUploadStatus('Generating AI insights...');
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      console.error('Sample load failed:', err);
      setErrorMessage(err.message || 'Failed to load sample dataset.');
      setIsUploading(false);
    }
  };

  const handleLoadIBMDataset = async () => {
    try {
      setIsUploading(true);
      setUploadStatus('Loading benchmark dataset (1,470 records)...');
      const result = await loadSampleDataset();
      setUploadStatus('Synthesizing dashboard...');
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      console.error('Benchmark load failed:', err);
      setErrorMessage(err.message || 'Failed to load benchmark dataset.');
      setIsUploading(false);
    }
  };

  return (
    <section className="upload-hero-container">
      {/* Glow Orbs */}
      <div className="hero-glow-orb orb-1"></div>
      <div className="hero-glow-orb orb-2"></div>

      <div className="upload-hero-card">
        {/* Top Badge */}
        <div className="hero-pill-badge">
          <Sparkles size={14} className="sparkle-icon" />
          <span>Interactive Attrition Intelligence &bull; Gemini 2.5 Flash</span>
        </div>

        {/* Title & Description */}
        <h1 className="hero-main-title">
          Upload Your Employee CSV to <span className="text-gradient-emerald">Generate Instant Analysis</span>
        </h1>
        <p className="hero-main-subtitle">
          No previous dataset details are shown. Add your workforce CSV to dynamically calculate turnover rates,
          generate 11 interactive visual breakdowns, pinpoint high-risk flight segments, and activate the AI Copilot.
        </p>

        {/* Drag & Drop Upload Zone */}
        <div
          className={`hero-dropzone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleFileChange}
            disabled={isUploading}
          />

          {isUploading ? (
            <div className="dropzone-loading">
              <Loader2 size={44} className="spin-animation text-emerald" />
              <h3 className="dropzone-title text-emerald">Synthesizing Dataset</h3>
              <p className="dropzone-text">{uploadStatus}</p>
              <div className="progress-bar-container">
                <div className="progress-bar-fill"></div>
              </div>
            </div>
          ) : (
            <div className="dropzone-content">
              <div className="dropzone-icon-circle">
                <UploadCloud size={38} className="text-emerald" />
              </div>
              <h3 className="dropzone-title">
                Drag and drop your employee CSV file here
              </h3>
              <p className="dropzone-text">
                Supports any standard HR or workforce CSV file with smart column auto-detection
              </p>
              <button
                type="button"
                className="btn-select-file"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                <FileSpreadsheet size={16} />
                <span>Browse Local CSV</span>
              </button>
            </div>
          )}
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="hero-error-banner">
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Quick Demo Options */}
        <div className="hero-quick-samples">
          <span className="quick-sample-label">Want to test without a file?</span>
          <button
            type="button"
            className="btn-quick-sample"
            onClick={handleSampleUpload}
            disabled={isUploading}
          >
            <Sparkles size={14} />
            <span>Load Quick Tech Startup Cohort (15 Employees)</span>
          </button>
          <button
            type="button"
            className="btn-quick-sample benchmark"
            onClick={handleLoadIBMDataset}
            disabled={isUploading}
          >
            <BarChart3 size={14} />
            <span>Load Benchmark IBM HR Cohort (1,470 Employees)</span>
          </button>
        </div>

        {/* Supported Schema Helper */}
        <div className="hero-schema-helper">
          <div className="schema-helper-title">
            <span>Smart Column Aliases Detected Automatically:</span>
          </div>
          <div className="schema-chips">
            <span className="schema-chip" title="attrition, left, churn, turnover, is_left, resigned">
              ✓ Attrition / Churn
            </span>
            <span className="schema-chip" title="department, dept, team, division, business_unit">
              ✓ Department / Team
            </span>
            <span className="schema-chip" title="job_role, role, position, title, designation">
              ✓ Job Role / Title
            </span>
            <span className="schema-chip" title="salary, monthly_income, income, compensation, pay">
              ✓ Monthly Income / Salary
            </span>
            <span className="schema-chip" title="overtime, over_time, ot">
              ✓ Overtime (Yes/No)
            </span>
            <span className="schema-chip" title="years_at_company, tenure, company_tenure, service_years">
              ✓ Company Tenure
            </span>
            <span className="schema-chip" title="age, employee_age">
              ✓ Employee Age
            </span>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <div className="hero-features-grid">
          <div className="hero-feature-card">
            <div className="feature-icon-wrapper mint">
              <Zap size={20} />
            </div>
            <h4>Instant KPI Engine</h4>
            <p>Calculates turnover rate, headcount, retention totals, and critical risk roles in milliseconds.</p>
          </div>

          <div className="hero-feature-card">
            <div className="feature-icon-wrapper emerald">
              <BarChart3 size={20} />
            </div>
            <h4>11 Visual Breakdowns</h4>
            <p>Interactive Chart.js visualizations covering departments, salaries, tenure, and satisfaction.</p>
          </div>

          <div className="hero-feature-card">
            <div className="feature-icon-wrapper amber">
              <ShieldAlert size={20} />
            </div>
            <h4>Root-Cause Factors</h4>
            <p>Ranks key drivers (overtime, pay, tenure) by differential percentage impact to reveal flight risks.</p>
          </div>

          <div className="hero-feature-card">
            <div className="feature-icon-wrapper teal">
              <BrainCircuit size={20} />
            </div>
            <h4>Grounded Gemini AI</h4>
            <p>Ask natural questions grounded exclusively in your uploaded data with zero hallucination.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
