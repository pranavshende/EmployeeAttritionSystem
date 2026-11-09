import React, { useState, useEffect } from 'react';
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
  Menu,
  X,
  ChevronRight,
  Database,
} from 'lucide-react';

export default function Header({
  datasetInfo = {},
  activeTab = 'home',
  onTabChange,
  onOpenUploadModal,
  onResetDataset,
  onOpenCopilot,
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const hasDataset = Boolean(datasetInfo && datasetInfo.has_dataset);
  const totalEmployees = (datasetInfo.total_employees || 0).toLocaleString();
  const datasetName = datasetInfo.dataset_name || 'No Dataset';

  // Automatically close mobile menu on desktop viewport resize
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Prevent background scroll when mobile menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'analysis', label: 'Analysis', icon: BarChart2 },
    { id: 'visualizations', label: 'Visualizations', icon: PieChart },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'copilot', label: 'AI Copilot', icon: Bot, isAi: true },
  ];

  const handleNavClick = (id) => {
    setMobileMenuOpen(false);
    if (id === 'copilot' && onOpenCopilot) {
      onOpenCopilot();
    } else if (onTabChange) {
      onTabChange(id);
    }
  };

  const handleUploadClick = () => {
    setMobileMenuOpen(false);
    if (onOpenUploadModal) {
      onOpenUploadModal();
    }
  };

  const handleResetClick = () => {
    setMobileMenuOpen(false);
    if (onResetDataset) {
      onResetDataset();
    }
  };

  return (
    <>
      <header className="dashboard-header-modern">
        {/* ── Left: Brand & Logo ── */}
        <div className="header-left">
          <div className="header-logo-badge" title="Employee Attrition Intelligence">
            <Activity size={20} strokeWidth={2.6} />
          </div>
          <div className="header-brand-text">
            <h1 className="header-brand-title">
              <span className="brand-full">Employee Attrition Intelligence</span>
              <span className="brand-short">AttritionAI</span>
            </h1>
            <p className="header-brand-subtitle">
              <span className="sub-dot"></span>
              Analytics &bull; Insights &bull; AI Copilot
            </p>
          </div>
        </div>

        {/* ── Center: Top Navigation Bar (Desktop) ── */}
        <nav className="header-center-nav" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-tab-btn ${isActive ? 'active' : ''} ${item.isAi ? 'nav-ai-btn' : ''}`}
                onClick={() => handleNavClick(item.id)}
              >
                <Icon size={14} className="nav-tab-icon" />
                <span>{item.label}</span>
                {item.isAi && <span className="nav-ai-tag">AI</span>}
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
              <FileSpreadsheet size={13} className="pill-icon" />
              <span className="dataset-label-text" title={datasetName}>
                {datasetName}
              </span>
              <span className="dataset-count-badge">({totalEmployees})</span>
            </div>
          ) : (
            <div className="status-pill no-dataset" title="No active dataset loaded">
              <span className="inactive-dot"></span>
              <FileSpreadsheet size={13} className="pill-icon" />
              <span className="dataset-label-text">No dataset</span>
            </div>
          )}

          {/* Clear/Reset button when dataset loaded */}
          {hasDataset && (
            <button
              type="button"
              className="btn-clear-dataset"
              onClick={handleResetClick}
              title="Clear dataset and return to upload screen"
            >
              <RotateCcw size={13} />
              <span className="btn-text-responsive">Clear</span>
            </button>
          )}

          {/* Upload CSV Button - Guaranteed single-line with white-space nowrap */}
          <button
            type="button"
            className="btn-header-upload"
            onClick={handleUploadClick}
            title="Upload employee CSV"
          >
            <UploadCloud size={14} />
            <span className="btn-upload-text">Upload CSV</span>
          </button>

          {/* Gemini AI Status Badge */}
          <div className="gemini-connected-badge" title="Gemini 2.5 Flash connected and active">
            <Sparkles size={13} className="sparkle-active" />
            <span className="gemini-badge-text">Gemini AI</span>
          </div>

          {/* User Profile Avatar */}
          <div className="user-profile-avatar" title="Pranav Shende (HR Admin)">
            <span>PS</span>
            <span className="avatar-online-dot"></span>
          </div>

          {/* Mobile / Tablet Hamburger Toggle */}
          <button
            type="button"
            className={`btn-mobile-menu-toggle ${mobileMenuOpen ? 'open' : ''}`}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close Menu' : 'Open Menu'}
            title={mobileMenuOpen ? 'Close Menu' : 'Open Menu'}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </header>

      {/* ── Mobile Slide-down Drawer / Menu ── */}
      {mobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <div className="mobile-menu-card" onClick={(e) => e.stopPropagation()}>
            {/* Mobile Menu Header */}
            <div className="mobile-menu-header">
              <div className="mobile-menu-brand">
                <div className="header-logo-badge small">
                  <Activity size={17} strokeWidth={2.6} />
                </div>
                <div>
                  <h2 className="mobile-menu-title">Attrition Intelligence</h2>
                  <p className="mobile-menu-subtitle">Workforce Analytics Hub</p>
                </div>
              </div>
              <button
                type="button"
                className="btn-close-mobile-menu"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </div>

            {/* Active Dataset Mobile Card */}
            <div className="mobile-dataset-card">
              <div className="mobile-dataset-header">
                <div className="mobile-dataset-left">
                  <span className={hasDataset ? 'live-pulse-dot' : 'inactive-dot'}></span>
                  <Database size={14} />
                  <span className="mobile-dataset-title">
                    {hasDataset ? 'Active Dataset' : 'Dataset Status'}
                  </span>
                </div>
                {hasDataset && (
                  <button
                    type="button"
                    className="btn-mobile-clear"
                    onClick={handleResetClick}
                    title="Reset dataset"
                  >
                    <RotateCcw size={12} />
                    <span>Clear</span>
                  </button>
                )}
              </div>
              <p className="mobile-dataset-name" title={datasetName}>
                {hasDataset ? datasetName : 'No dataset loaded yet'}
              </p>
              {hasDataset && (
                <div className="mobile-dataset-stats">
                  <span>{totalEmployees} employee records loaded</span>
                </div>
              )}
            </div>

            {/* Mobile Navigation List */}
            <nav className="mobile-nav-list" aria-label="Mobile Navigation Drawer">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`mobile-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => handleNavClick(item.id)}
                  >
                    <div className="mobile-nav-item-left">
                      <div className={`mobile-nav-icon-wrap ${isActive ? 'active' : ''}`}>
                        <Icon size={16} />
                      </div>
                      <span className="mobile-nav-label">{item.label}</span>
                    </div>
                    {item.isAi ? (
                      <span className="nav-ai-tag">AI Copilot</span>
                    ) : (
                      <ChevronRight size={14} className="mobile-nav-chevron" />
                    )}
                  </button>
                );
              })}
            </nav>

            {/* Mobile Action Buttons */}
            <div className="mobile-menu-actions">
              <button
                type="button"
                className="btn-mobile-upload"
                onClick={handleUploadClick}
              >
                <UploadCloud size={16} />
                <span>Upload CSV Dataset</span>
              </button>
            </div>

            {/* Mobile Menu Footer: Gemini Badge & User Info */}
            <div className="mobile-menu-footer">
              <div className="mobile-ai-status">
                <Sparkles size={14} className="sparkle-active" />
                <span>Gemini 2.5 Flash Connected</span>
              </div>
              <div className="mobile-user-row">
                <div className="user-profile-avatar small">
                  <span>PS</span>
                </div>
                <div className="mobile-user-details">
                  <span className="mobile-user-name">Pranav Shende</span>
                  <span className="mobile-user-role">HR Analytics Admin</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
