import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import Header from './components/Header';
import UploadHero from './components/UploadHero';
import KpiCards from './components/KpiCards';
import FilterBar from './components/FilterBar';
import ChartsGrid from './components/ChartsGrid';
import HighRiskTable from './components/HighRiskTable';
import ChatbotDrawer from './components/ChatbotDrawer';
import UploadModal from './components/UploadModal';
import AiInsightsBanner from './components/AiInsightsBanner';
import {
  fetchKPIs,
  fetchChart,
  fetchHighRisk,
  fetchFilterOptions,
  fetchFiltered,
  fetchDatasetInfo,
  clearDataset,
} from './api';

export default function App() {
  const [kpis, setKpis] = useState(null);
  const [filterOptions, setFilterOptions] = useState({});
  const [currentFilters, setCurrentFilters] = useState({});
  const [chartsData, setChartsData] = useState({});
  const [highRiskData, setHighRiskData] = useState({});
  const [highRiskPage, setHighRiskPage] = useState(1);
  const [datasetInfo, setDatasetInfo] = useState({ has_dataset: false });
  const [aiSummary, setAiSummary] = useState('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Load analytics when a dataset is confirmed active
  const loadBaselineData = async () => {
    try {
      setIsLoading(true);
      const [
        kpisRes,
        deptRes,
        roleRes,
        ageRes,
        incomeRes,
        factorsRes,
        overtimeRes,
        tenureRes,
        satisfactionRes,
        travelRes,
        stockRes,
        worklifeRes,
        riskRes,
        infoRes,
        filtersRes,
      ] = await Promise.all([
        fetchKPIs().catch((e) => { console.error('fetchKPIs failed:', e); return null; }),
        fetchChart('department').catch(() => []),
        fetchChart('job-role').catch(() => []),
        fetchChart('age').catch(() => []),
        fetchChart('income').catch(() => []),
        fetchChart('factors').catch(() => []),
        fetchChart('overtime').catch(() => []),
        fetchChart('tenure').catch(() => []),
        fetchChart('satisfaction').catch(() => ({ job_satisfaction: [], env_satisfaction: [] })),
        fetchChart('travel').catch(() => []),
        fetchChart('stock-options').catch(() => []),
        fetchChart('work-life-balance').catch(() => []),
        fetchHighRisk(1, 15).catch((e) => { console.error('fetchHighRisk failed:', e); return { employees: [], total: 0, total_count: 0, page: 1, total_pages: 1 }; }),
        fetchDatasetInfo().catch(() => ({ has_dataset: false })),
        fetchFilterOptions().catch(() => ({})),
      ]);

      setKpis(kpisRes);
      setChartsData({
        department: deptRes,
        jobRole: roleRes,
        age: ageRes,
        income: incomeRes,
        factors: factorsRes,
        overtime: overtimeRes,
        tenure: tenureRes,
        satisfaction: satisfactionRes,
        travel: travelRes,
        stock: stockRes,
        worklife: worklifeRes,
      });
      setHighRiskData(riskRes);
      setHighRiskPage(1);
      setDatasetInfo(infoRes || { has_dataset: false });
      if (infoRes && infoRes.ai_summary) {
        setAiSummary(infoRes.ai_summary);
      }
      setFilterOptions(filtersRes || {});
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // On initial mount: inspect backend to see if a dataset is already active
  useEffect(() => {
    const checkActiveDataset = async () => {
      try {
        setIsLoading(true);
        const info = await fetchDatasetInfo();
        if (info && info.has_dataset) {
          setDatasetInfo(info);
          if (info.ai_summary) setAiSummary(info.ai_summary);
          await loadBaselineData();
        } else {
          // No dataset loaded — keep clean empty hero state
          setDatasetInfo({ has_dataset: false });
          setKpis(null);
          setChartsData({});
          setHighRiskData({});
          setAiSummary('');
          setIsLoading(false);
        }
      } catch (err) {
        console.warn('Initial dataset check error:', err);
        setDatasetInfo({ has_dataset: false });
        setIsLoading(false);
      }
    };

    checkActiveDataset();
  }, []);

  // Filter change handler
  const handleFilterChange = async (key, value) => {
    const updated = { ...currentFilters };
    if (!value) {
      delete updated[key];
    } else {
      updated[key] = value;
    }
    setCurrentFilters(updated);

    // If no active filters, restore baseline
    const activeKeys = Object.keys(updated);
    if (activeKeys.length === 0) {
      loadBaselineData();
      return;
    }

    // Build query params
    const queryParams = {};
    if (updated.department) queryParams.department = updated.department;
    if (updated.overtime) queryParams.overtime = updated.overtime;
    if (updated.job_role) queryParams.job_role = updated.job_role;
    if (updated.gender) queryParams.gender = updated.gender;

    if (updated.age_band) {
      const b = updated.age_band;
      if (b === '18-25') { queryParams.age_min = 18; queryParams.age_max = 25; }
      else if (b === '26-35') { queryParams.age_min = 26; queryParams.age_max = 35; }
      else if (b === '36-45') { queryParams.age_min = 36; queryParams.age_max = 45; }
      else if (b === '46-55') { queryParams.age_min = 46; queryParams.age_max = 55; }
      else if (b === '56+') { queryParams.age_min = 56; queryParams.age_max = 99; }
    }

    try {
      const filtered = await fetchFiltered(queryParams);
      if (filtered) {
        setKpis((prev) => ({
          ...prev,
          total_employees: filtered.total_employees,
          attrition_count: filtered.attrition_count,
          retention_count: filtered.retention_count,
          attrition_rate: filtered.attrition_rate,
          avg_age: filtered.avg_age,
          avg_monthly_income: filtered.avg_monthly_income,
        }));

        if (filtered.charts) {
          setChartsData((prev) => ({
            ...prev,
            department: filtered.charts.department || prev.department,
            jobRole: filtered.charts.job_role || prev.jobRole,
            age: filtered.charts.age || prev.age,
            overtime: filtered.charts.overtime || prev.overtime,
            tenure: filtered.charts.tenure || prev.tenure,
          }));
        }
      }
    } catch (e) {
      console.error('Filtering failed:', e);
    }
  };

  const handleResetFilters = () => {
    setCurrentFilters({});
    loadBaselineData();
  };

  const handleHighRiskPageChange = async (newPage) => {
    try {
      const res = await fetchHighRisk(newPage, 15);
      setHighRiskData(res);
      setHighRiskPage(newPage);
    } catch (e) {
      console.error('High risk page load failed:', e);
    }
  };

  // Callback when a new CSV is uploaded successfully
  const handleUploadSuccess = (result) => {
    setCurrentFilters({});
    if (result.dataset_info) {
      setDatasetInfo(result.dataset_info);
    }
    if (result.ai_summary) {
      setAiSummary(result.ai_summary);
    }
    // Instantly regenerate dashboard from the newly uploaded dataset
    loadBaselineData();
  };

  // Callback to clear dataset and return to clean empty hero state
  const handleResetDataset = async () => {
    try {
      setIsLoading(true);
      await clearDataset();
      setAiSummary('');
      setCurrentFilters({});
      setKpis(null);
      setChartsData({});
      setHighRiskData({});
      setDatasetInfo({ has_dataset: false });
    } catch (e) {
      console.error('Clear dataset failed:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const hasDataset = Boolean(datasetInfo && datasetInfo.has_dataset);

  return (
    <div className="app-container">
      {/* ── Top Header ── */}
      <Header
        datasetInfo={datasetInfo}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        onResetDataset={handleResetDataset}
      />

      {/* ── Main View: Loading | Empty Hero (No Previous CSV) | Full Analytics ── */}
      {isLoading ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '55vh',
          gap: '16px',
        }}>
          <Loader2 size={44} className="spin-animation text-emerald" />
          <p style={{ color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.95rem' }}>
            Synthesizing workforce metrics & generating AI analytics...
          </p>
        </div>
      ) : !hasDataset ? (
        /* Empty State: Absolutely no previous CSV details shown */
        <UploadHero onUploadSuccess={handleUploadSuccess} />
      ) : (
        /* Generated On-the-spot Analytics: Shown ONLY after adding a CSV */
        <>
          {/* ── AI Executive Synthesis Banner (Generated on the spot by Gemini) ── */}
          <AiInsightsBanner datasetInfo={datasetInfo} aiSummary={aiSummary} />

          {/* ── Multidimensional Filter Bar ── */}
          <FilterBar
            filterOptions={filterOptions}
            currentFilters={currentFilters}
            onFilterChange={handleFilterChange}
            onReset={handleResetFilters}
          />

          {/* ── KPI Metrics Cards ── */}
          <KpiCards kpis={kpis} />

          {/* ── 11 Interactive Charts ── */}
          <ChartsGrid chartsData={chartsData} />

          {/* ── High-Risk Watchlist ── */}
          <HighRiskTable
            highRiskData={highRiskData}
            currentPage={highRiskPage}
            onPageChange={handleHighRiskPageChange}
          />
        </>
      )}

      {/* ── Conversational AI Copilot (Tuned dynamically to active dataset) ── */}
      <ChatbotDrawer datasetInfo={datasetInfo} />

      {/* ── CSV Upload & AI Generation Modal ── */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}
