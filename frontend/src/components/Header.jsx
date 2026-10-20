import React from 'react';
import {
  Activity,
  Sparkles,
  UploadCloud,
  RotateCcw,
  FileSpreadsheet,
  Home,
  BarChart2,
  PieChart,
  FileText,
  Bot,
} from 'lucide-react';

export default function Header({
  datasetInfo = {},
  activeTab = 'home',
  onTabChange,
  onOpenUploadModal,
  onResetDataset,
  onOpenCopilot,
}) {
  const hasDataset = Boolean(datasetInfo && datasetInfo.has_dataset);
  const totalEmployees = (datasetInfo.total_employees || 0).toLocaleString();
  const datasetName = datasetInfo.dataset_name || 'No Dataset';

  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'analysis', label: 'Analysis', icon: BarChart2 },
    { id: 'visualizations', label: 'Visualizations', icon: PieChart },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'copilot', label: 'AI Copilot', icon: Bot },
  ];

  const handleNavClick = (id) => {
    if (id === 'copilot' && onOpenCopilot) {
      onOpenCopilot();
    } else if (onTabChange) {
      onTabChange(id);
    }
  };

  return (
    <header className="dashboard-header-modern">
      {/* ── Left: Brand & Logo ── */}
      <div className="header-left">
        <div className="header-logo-badge">
          <Activity size={22} strokeWidth={2.6} />
        </div>
        <div className="header-brand-text">
          <h1 className="header-brand-title">Employee Attrition Intelligence</h1>
          <p className="header-brand-subtitle">Analytics &bull; Insights &bull; AI Copilot</p>
        </div>
      </div>

      {/* ── Center: Top Navigation Bar ── */}
      <nav className="header-center-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => handleNavClick(item.id)}
            >
              <Icon size={14} className="nav-tab-icon" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* ── Right: Dataset Status, Actions & Profile ── */}
      <div className="header-right-actions">
        {/* Dataset Status Pill */}
        {hasDataset ? (
          <div
            className="status-pill dataset-active"
            title={`Active dataset: ${datasetName} (${totalEmployees} records)`}
          >
            <span className="live-pulse-dot"></span>
            <FileSpreadsheet size={13} />
            <span className="dataset-label-text">
              {datasetName} ({totalEmployees})
            </span>
          </div>
        ) : (
          <div className="status-pill no-dataset" title="No active dataset loaded">
            <span className="inactive-dot"></span>
            <FileSpreadsheet size={13} />
            <span>No dataset loaded</span>
          </div>
        )}

        {/* Clear/Reset button when dataset loaded */}
        {hasDataset && (
          <button
            type="button"
            className="btn-clear-dataset"
            onClick={onResetDataset}
            title="Clear dataset and return to upload screen"
          >
            <RotateCcw size={13} />
            <span>Clear</span>
          </button>
        )}

        {/* Upload CSV Button */}
        <button
          type="button"
          className="btn-header-upload"
          onClick={onOpenUploadModal}
          title="Upload employee CSV"
        >
          <UploadCloud size={14} />
          <span>Upload CSV</span>
        </button>

        {/* Gemini AI Status Badge */}
        <div className="gemini-connected-badge" title="Gemini 2.5 Flash connected and active">
          <Sparkles size={13} className="sparkle-active" />
          <span>Gemini AI Connected</span>
        </div>

        {/* User Profile Avatar */}
        <div className="user-profile-avatar" title="Pranav Shende (HR Admin)">
          <span>PS</span>
        </div>
      </div>
    </header>
  );
}
