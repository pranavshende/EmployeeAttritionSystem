import React, { useState, useEffect } from 'react';
import {
  Activity,
  Upload,
  RotateCcw,
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
      if (window.innerWidth >= 1080) {
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
    { id: 'home', label: 'Home' },
    { id: 'analysis', label: 'Analytics' },
    { id: 'visualizations', label: 'Visualizations' },
    { id: 'reports', label: 'Risk Reports' },
    { id: 'copilot', label: 'AI Copilot' },
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
      if (window.confirm('Reset dataset to default view?')) {
        onResetDataset();
      }
    }
  };

  return (
    <>
      <header className="dashboard-header-modern">
        {/* ── Left: Brand & Logo ── */}
        <div className="header-left">
          <div className="header-logo-badge" title="Attrition Intelligence">
            <Activity size={18} strokeWidth={2.4} color="#ffffff" />
          </div>
          <span className="header-brand-title">Attrition Intelligence</span>
        </div>

        {/* ── Center: Top Navigation Bar (Exact Segmented Pills) ── */}
        <nav className="header-center-nav" aria-label="Main Navigation">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-tab-btn ${isActive ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* ── Right: Dataset Status, Actions & Upload ── */}
        <div className="header-right-actions">
          {/* Active: 1,470 Employees Pill */}
          <div
            className={`header-active-pill ${hasDataset ? 'active clickable' : 'empty'}`}
            title={hasDataset ? `Active File: ${datasetName} (${totalEmployees} records) • Click to reset` : 'No dataset active • Click to upload'}
            onClick={hasDataset ? handleResetClick : handleUploadClick}
          >
            {hasDataset ? `Active: ${totalEmployees} Employees` : 'No Dataset Active'}
          </div>

          {/* Square Action Icon Button (Upload tray icon matching screenshot) */}
          <button
            type="button"
            className="btn-square-action"
            onClick={handleUploadClick}
            title="Upload CSV dataset"
            aria-label="Upload CSV dataset"
          >
            <Upload size={14} strokeWidth={2.2} />
          </button>

          {/* Upload CSV Primary Green Button */}
          <button
            type="button"
            className="btn-primary-upload"
            onClick={handleUploadClick}
            title="Upload employee CSV dataset"
          >
            Upload CSV
          </button>

          {/* Mobile / Tablet Hamburger Toggle */}
          <button
            type="button"
            className={`btn-mobile-menu-toggle ${mobileMenuOpen ? 'open' : ''}`}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? 'Close Menu' : 'Open Menu'}
            title={mobileMenuOpen ? 'Close Menu' : 'Open Menu'}
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </header>

      {/* ── Mobile Slide-down Drawer / Menu ── */}
      {mobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={() => setMobileMenuOpen(false)}>
          <div className="mobile-menu-card" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-menu-header">
              <div className="mobile-menu-brand">
                <div className="header-logo-badge small">
                  <Activity size={16} strokeWidth={2.4} color="#ffffff" />
                </div>
                <div>
                  <h2 className="mobile-menu-title">Attrition Intelligence</h2>
                  <p className="mobile-menu-subtitle">Enterprise HR Analytics</p>
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

            <div className="mobile-dataset-card">
              <div className="mobile-dataset-header">
                <div className="mobile-dataset-left">
                  <Database size={14} />
                  <span className="mobile-dataset-title">
                    {hasDataset ? `Active: ${totalEmployees} Employees` : 'No Dataset Active'}
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
              {hasDataset && (
                <p className="mobile-dataset-name" title={datasetName}>
                  {datasetName}
                </p>
              )}
            </div>

            <nav className="mobile-nav-list" aria-label="Mobile Navigation Drawer">
              {navItems.map((item) => {
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`mobile-nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => handleNavClick(item.id)}
                  >
                    <span className="mobile-nav-label">{item.label}</span>
                    <ChevronRight size={14} className="mobile-nav-chevron" />
                  </button>
                );
              })}
            </nav>

            <div className="mobile-menu-actions">
              <button
                type="button"
                className="btn-mobile-upload"
                onClick={handleUploadClick}
              >
                Upload CSV Dataset
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
