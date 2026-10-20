import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  Sparkles,
  BarChart3,
  ShieldAlert,
  BrainCircuit,
  Zap,
  Users,
  ChevronRight,
  Send,
  Paperclip,
  Maximize2,
  MoreHorizontal,
  Lightbulb,
  Bot,
  AlertCircle,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import { uploadDataset, loadSampleDataset, sendChatMessage } from '../api';

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

const DEFAULT_SUGGESTIONS = [
  'What is the overall attrition rate?',
  'Which department has the highest attrition?',
  'Show me key factors driving attrition.',
  'List employees most likely to leave.',
  'Compare attrition across job roles.',
  'Give me actionable recommendations to reduce attrition.',
];

export default function UploadHero({ onUploadSuccess, onOpenCopilot }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  // Copilot Interactive State
  const [copilotInput, setCopilotInput] = useState('');
  const [isCopilotSending, setIsCopilotSending] = useState(false);
  const [copilotConversation, setCopilotConversation] = useState([]);
  const [showConversation, setShowConversation] = useState(false);
  const copilotEndRef = useRef(null);

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

  // ── Copilot Actions ──
  const handleCopilotSend = async (customPrompt) => {
    const prompt = (customPrompt || copilotInput).trim();
    if (!prompt || isCopilotSending) return;

    setShowConversation(true);
    const userMsg = { id: Date.now(), sender: 'user', text: prompt };
    setCopilotConversation((prev) => [...prev, userMsg]);
    setCopilotInput('');
    setIsCopilotSending(true);

    try {
      const res = await sendChatMessage(prompt, 'hero_copilot_session');
      const botMsg = {
        id: Date.now() + 1,
        sender: 'bot',
        text: res.response || "I've processed your request.",
        source: res.source,
      };
      setCopilotConversation((prev) => [...prev, botMsg]);
    } catch (e) {
      console.error('Copilot send failed:', e);
      setCopilotConversation((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'bot',
          text:
            "📊 **Dataset required for precise cohort metrics.**\n\nPlease upload your employee CSV file using the box on the left, or click below to load our sample tech startup cohort (15 employees) to immediately see these calculations!",
          isActionFallback: true,
        },
      ]);
    } finally {
      setIsCopilotSending(false);
      setTimeout(() => {
        copilotEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  return (
    <div className="hero-split-layout">
      {/* Hidden File Input for Paperclip or Browse button */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        disabled={isUploading}
      />

      {/* ═════════════════════════════════════════════════════
          LEFT COLUMN: Hero, Upload Dropzone, Samples, Highlights
          ═════════════════════════════════════════════════════ */}
      <div className="hero-left-col">
        {/* Top Header Section with Title + Floating Preview Cluster */}
        <div className="hero-header-section">
          <div className="hero-header-content">
            <div className="hero-ai-badge">
              <Sparkles size={13} className="sparkle-active" />
              <span>AI-Powered Workforce Analytics</span>
            </div>
            <h1 className="hero-title-main">
              Turn workforce data into <br />
              <span className="hero-title-emerald">clear attrition insights</span>
            </h1>
            <p className="hero-subtitle-text">
              Upload your employee CSV to automatically calculate turnover rates, generate 11 interactive visual
              breakdowns, pinpoint high-risk flight segments, and activate the AI Copilot for deeper analysis and
              recommendations.
            </p>
          </div>

          {/* Floating Metric Illustrations Cluster (Exact Screenshot 2 Parity) */}
          <div className="hero-preview-cluster" aria-hidden="true">
            {/* Top Card: Attrition Rate & Wave */}
            <div className="floating-preview-card">
              <div className="preview-rate-header">
                <span>Attrition Rate</span>
                <span className="preview-rate-badge">&darr; -2.4%</span>
              </div>
              <div className="preview-rate-val-row">
                <span className="preview-rate-number">16.2%</span>
              </div>
              <svg viewBox="0 0 140 34" className="preview-sparkline-svg">
                <defs>
                  <linearGradient id="previewWaveGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.32" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path
                  d="M 0 24 Q 28 8, 55 18 T 105 7 T 140 14 L 140 34 L 0 34 Z"
                  fill="url(#previewWaveGrad)"
                />
                <path
                  d="M 0 24 Q 28 8, 55 18 T 105 7 T 140 14"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                />
              </svg>
            </div>

            {/* Bottom Row: High Risk Segments & AI Insights */}
            <div className="preview-mini-row">
              {/* High Risk Segments Mini Card */}
              <div className="floating-preview-card" style={{ padding: '10px 12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <div
                    style={{
                      width: '18px',
                      height: '18px',
                      borderRadius: '50%',
                      background: '#fee2e2',
                      color: '#ef4444',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Users size={10} />
                  </div>
                  <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#334155' }}>High Risk</span>
                </div>
                <div className="preview-bars">
                  <div className="preview-bar-item" style={{ height: '10px' }}></div>
                  <div className="preview-bar-item" style={{ height: '18px' }}></div>
                  <div className="preview-bar-item" style={{ height: '14px' }}></div>
                  <div className="preview-bar-item" style={{ height: '22px' }}></div>
                  <div className="preview-bar-item" style={{ height: '12px' }}></div>
                </div>
              </div>

              {/* AI Insights Mini Card */}
              <div className="floating-preview-card" style={{ padding: '10px 12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Sparkles size={11} style={{ color: '#059669' }} />
                  <span style={{ fontSize: '0.66rem', fontWeight: 700, color: '#334155' }}>AI Insights</span>
                </div>
                <svg viewBox="0 0 32 32" className="preview-donut-svg">
                  <circle cx="16" cy="16" r="12" fill="none" stroke="#e2e8f0" strokeWidth="3.2" />
                  <circle
                    cx="16"
                    cy="16"
                    r="12"
                    fill="none"
                    stroke="#059669"
                    strokeWidth="3.2"
                    strokeDasharray="75.4"
                    strokeDashoffset="22"
                    strokeLinecap="round"
                    transform="rotate(-90 16 16)"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* ── Drag & Drop Upload Zone ── */}
        <div
          className={`dropzone-emerald ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
        >
          {isUploading ? (
            <div style={{ padding: '24px 0' }}>
              <Loader2 size={44} className="spin-animation" style={{ color: '#059669', margin: '0 auto 12px' }} />
              <h3 className="dropzone-heading" style={{ color: '#059669' }}>
                Synthesizing Dataset with AI
              </h3>
              <p className="dropzone-subtext" style={{ fontWeight: 600 }}>
                {uploadStatus}
              </p>
              <div
                style={{
                  maxWidth: '300px',
                  height: '6px',
                  background: '#a7f3d0',
                  borderRadius: '3px',
                  margin: '12px auto 0',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: '100%',
                    height: '100%',
                    background: '#059669',
                    animation: 'pulse 1.2s infinite ease-in-out',
                  }}
                ></div>
              </div>
            </div>
          ) : (
            <div>
              <div className="dropzone-circle-icon">
                <UploadCloud size={28} />
              </div>
              <h3 className="dropzone-heading">Drag and drop your employee CSV file here</h3>
              <p className="dropzone-subtext">
                Supports any standard HR or workforce CSV file with smart column auto-detection.
              </p>
              <button
                type="button"
                className="btn-browse-emerald"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
              >
                <FileSpreadsheet size={16} />
                <span>Browse Local CSV</span>
              </button>
              <p className="dropzone-privacy-footer">
                Your data stays private and is only used for analysis in this session.
              </p>
            </div>
          )}
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '12px 16px',
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              color: '#dc2626',
              fontSize: '0.85rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Sample Datasets Row */}
        <div className="hero-sample-row">
          <span className="sample-row-label">Want to try a sample dataset?</span>
          <button
            type="button"
            className="btn-sample-chip"
            onClick={handleSampleUpload}
            disabled={isUploading}
          >
            <Users size={14} style={{ color: '#0284c7' }} />
            <span>Load Quick Test Startup Cohort (15 Employees)</span>
          </button>
          <button
            type="button"
            className="btn-sample-chip"
            onClick={handleLoadIBMDataset}
            disabled={isUploading}
          >
            <BarChart3 size={14} style={{ color: '#059669' }} />
            <span>Load Benchmark IBM HR Cohort (1,470 Employees)</span>
          </button>
        </div>

        {/* Smart Column Aliases */}
        <div className="smart-aliases-box">
          <div className="smart-aliases-title">Smart Column Aliases Detected Automatically:</div>
          <div className="smart-aliases-chips">
            <span className="smart-alias-pill">✓ Attrition / Churn</span>
            <span className="smart-alias-pill">✓ Department / Team</span>
            <span className="smart-alias-pill">✓ Job Role / Title</span>
            <span className="smart-alias-pill">✓ Monthly Income / Salary</span>
            <span className="smart-alias-pill">✓ Overtime (Yes/No)</span>
            <span className="smart-alias-pill">✓ Company Tenure</span>
            <span className="smart-alias-pill">✓ Employee Age</span>
          </div>
        </div>

        {/* 4 Feature Highlights Grid */}
        <div className="hero-features-grid" style={{ marginTop: '10px' }}>
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
            <p>Interactive charts &amp; visualizations covering departments, salaries, tenure, and satisfaction.</p>
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

      {/* ═════════════════════════════════════════════════════
          RIGHT COLUMN: AttritionAI Copilot Card (Interactive)
          ═════════════════════════════════════════════════════ */}
      <div className="hero-copilot-container">
        {/* Header Bar */}
        <div className="copilot-header-bar">
          <div className="copilot-header-left">
            <div className="copilot-sparkle-badge">
              <Sparkles size={17} />
            </div>
            <div>
              <h3 className="copilot-title-text">AttritionAI Copilot</h3>
              <div className="copilot-status-line">
                <span className="copilot-status-dot-green"></span>
                <span>Online &bull; Ready for your analysis</span>
              </div>
            </div>
          </div>
          <div className="copilot-header-actions">
            {showConversation && (
              <button
                type="button"
                className="copilot-icon-btn"
                onClick={() => setShowConversation(false)}
                title="Back to Suggested Prompts"
              >
                <RotateCcw size={14} />
              </button>
            )}
            <button
              type="button"
              className="copilot-icon-btn"
              onClick={onOpenCopilot}
              title="Expand to Full Copilot Drawer"
            >
              <Maximize2 size={14} />
            </button>
            <button
              type="button"
              className="copilot-icon-btn"
              onClick={onOpenCopilot}
              title="More Options"
            >
              <MoreHorizontal size={14} />
            </button>
          </div>
        </div>

        {/* Body Area */}
        <div className="copilot-body-area">
          {/* Default Welcome Bubble */}
          <div className="copilot-greeting-row">
            <div className="copilot-bot-avatar">
              <Bot size={18} />
            </div>
            <div className="copilot-greeting-bubble">
              Hi! I'm your AttritionAI Copilot powered by Gemini. Upload your employee dataset and I can help you
              analyze attrition, explore trends, find at-risk segments, and suggest actionable recommendations.
            </div>
          </div>

          {/* Conversation History (if user clicked or typed) */}
          {showConversation && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {copilotConversation.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '92%',
                  }}
                >
                  <div
                    style={{
                      padding: '10px 14px',
                      borderRadius: '12px',
                      fontSize: '0.8rem',
                      lineHeight: '1.45',
                      background: msg.sender === 'user' ? '#059669' : '#f8fafc',
                      color: msg.sender === 'user' ? '#ffffff' : '#1e293b',
                      border: msg.sender === 'user' ? 'none' : '1px solid #e2e8f0',
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {msg.text}
                  </div>

                  {/* Fallback Action Buttons if no dataset */}
                  {msg.isActionFallback && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        onClick={handleSampleUpload}
                        className="btn-sample-chip"
                        style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#047857' }}
                      >
                        <Users size={12} />
                        <span>Load Startup Sample</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="btn-sample-chip"
                      >
                        <FileSpreadsheet size={12} />
                        <span>Browse CSV</span>
                      </button>
                    </div>
                  )}
                </div>
              ))}

              {isCopilotSending && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', alignSelf: 'flex-start' }}>
                  <div className="copilot-bot-avatar" style={{ width: '26px', height: '26px' }}>
                    <Bot size={14} />
                  </div>
                  <div className="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              )}
              <div ref={copilotEndRef} />
            </div>
          )}

          {/* Suggestions Box (Always accessible or when conversation not started) */}
          {!showConversation && (
            <div className="copilot-suggestions-card">
              <div className="copilot-suggestions-heading">
                <Lightbulb size={15} style={{ color: '#059669' }} />
                <span>Try asking something like:</span>
              </div>
              <div className="copilot-suggestions-list">
                {DEFAULT_SUGGESTIONS.map((suggestion, index) => (
                  <button
                    key={index}
                    type="button"
                    className="copilot-prompt-card"
                    onClick={() => handleCopilotSend(suggestion)}
                    disabled={isCopilotSending}
                  >
                    <span>{suggestion}</span>
                    <ChevronRight size={14} className="prompt-chevron" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="copilot-input-zone">
          <div className="copilot-input-box">
            <button
              type="button"
              className="btn-copilot-clip"
              onClick={() => fileInputRef.current?.click()}
              title="Attach / Upload CSV"
            >
              <Paperclip size={16} />
            </button>
            <input
              type="text"
              className="copilot-text-input"
              placeholder="Ask a question about your employee data..."
              value={copilotInput}
              onChange={(e) => setCopilotInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleCopilotSend();
                }
              }}
              disabled={isCopilotSending}
            />
            <button
              type="button"
              className="btn-copilot-send-round"
              onClick={() => handleCopilotSend()}
              disabled={!copilotInput.trim() || isCopilotSending}
              title="Send question to Copilot"
            >
              {isCopilotSending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
            </button>
          </div>
          <p className="copilot-input-disclaimer">
            Grounded in your uploaded dataset &bull; Powered by Gemini &bull; No hallucinations
          </p>
        </div>
      </div>
    </div>
  );
}
