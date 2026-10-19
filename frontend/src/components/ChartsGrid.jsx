import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

// Global light theme Chart defaults
ChartJS.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
ChartJS.defaults.color = '#475569';
ChartJS.defaults.borderColor = '#f1f5f9';
ChartJS.defaults.plugins.tooltip.backgroundColor = '#ffffff';
ChartJS.defaults.plugins.tooltip.titleColor = '#0f172a';
ChartJS.defaults.plugins.tooltip.bodyColor = '#334155';
ChartJS.defaults.plugins.tooltip.borderColor = '#e2e8f0';
ChartJS.defaults.plugins.tooltip.borderWidth = 1;
ChartJS.defaults.plugins.tooltip.padding = 10;
ChartJS.defaults.plugins.tooltip.cornerRadius = 8;
ChartJS.defaults.plugins.tooltip.boxPadding = 4;

export default function ChartsGrid({ chartsData = {} }) {
  const {
    department = [],
    jobRole = [],
    age = [],
    income = [],
    factors = [],
    overtime = [],
    tenure = [],
    satisfaction = {},
    travel = [],
    stock = [],
    worklife = [],
  } = chartsData;

  // Dynamic color palettes for arbitrary dataset categories
  const deptPalette = [
    '#10b981', '#059669', '#34d399', '#6ee7b7', '#047857', '#0f766e', '#14b8a6', '#2dd4bf', '#0284c7', '#6366f1'
  ];
  const travelPalette = ['#ef4444', '#f59e0b', '#10b981', '#06b6d4', '#8b5cf6'];

  // 1. Department Doughnut Chart
  const deptChartData = {
    labels: department.map((d) => d.label),
    datasets: [
      {
        data: department.map((d) => d.attrition ?? d.total ?? 0),
        backgroundColor: department.map((_, i) => deptPalette[i % deptPalette.length]),
        borderColor: '#ffffff',
        borderWidth: 2,
        hoverOffset: 6,
      },
    ],
  };

  // 2. Job Role Horizontal Bar Chart
  const sortedRoles = [...jobRole].sort((a, b) => (b.rate || 0) - (a.rate || 0));
  const roleChartData = {
    labels: sortedRoles.map((d) => d.label),
    datasets: [
      {
        label: 'Attrition Rate (%)',
        data: sortedRoles.map((d) => d.rate || 0),
        backgroundColor: sortedRoles.map((d) =>
          d.rate > 25 ? 'rgba(239, 68, 68, 0.85)' : d.rate > 15 ? 'rgba(245, 158, 11, 0.85)' : 'rgba(16, 185, 129, 0.85)'
        ),
        borderColor: sortedRoles.map((d) => (d.rate > 25 ? '#ef4444' : d.rate > 15 ? '#f59e0b' : '#10b981')),
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  // 3. Age Band Distribution Bar + Line
  const ageChartData = {
    labels: age.map((d) => d.label),
    datasets: [
      {
        type: 'bar',
        label: 'Attrition Count',
        data: age.map((d) => d.attrition || 0),
        backgroundColor: 'rgba(239, 68, 68, 0.8)',
        borderRadius: 4,
        yAxisID: 'y',
      },
      {
        type: 'line',
        label: 'Attrition Rate (%)',
        data: age.map((d) => d.rate || 0),
        borderColor: '#059669',
        backgroundColor: '#059669',
        borderWidth: 2.5,
        pointRadius: 4,
        yAxisID: 'y1',
      },
    ],
  };

  // 4. Monthly Income Bands Stacked
  const incomeChartData = {
    labels: income.map((d) => d.label),
    datasets: [
      {
        label: 'Retained',
        data: income.map((d) => d.retention || 0),
        backgroundColor: 'rgba(16, 185, 129, 0.75)',
        borderRadius: 4,
      },
      {
        label: 'Departed',
        data: income.map((d) => d.attrition || 0),
        backgroundColor: 'rgba(239, 68, 68, 0.85)',
        borderRadius: 4,
      },
    ],
  };

  // 5. Top Contributing Risk Drivers
  const factorsChartData = {
    labels: factors.map((d) => {
      const high = d.high_risk_cohort || d.high_risk_group || '';
      const low = d.low_risk_cohort || d.low_risk_group || '';
      return high && low ? `${d.factor} (${high} vs ${low})` : d.factor;
    }),
    datasets: [
      {
        label: 'Attrition Delta (+pp)',
        data: factors.map((d) => d.impact_pp ?? d.impact ?? 0),
        backgroundColor: factors.map((_, i) => (i === 0 ? 'rgba(239, 68, 68, 0.9)' : 'rgba(16, 185, 129, 0.85)')),
        borderColor: factors.map((_, i) => (i === 0 ? '#ef4444' : '#059669')),
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  // 6. OverTime Comparison
  const overtimeChartData = {
    labels: overtime.map((d) => `OverTime: ${d.label}`),
    datasets: [
      {
        label: 'Attrition Rate (%)',
        data: overtime.map((d) => d.rate || 0),
        backgroundColor: overtime.map((d) => (d.label === 'Yes' ? 'rgba(239, 68, 68, 0.85)' : 'rgba(16, 185, 129, 0.85)')),
        borderColor: overtime.map((d) => (d.label === 'Yes' ? '#ef4444' : '#10b981')),
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  };

  // 7. Tenure Band Breakdown
  const tenureChartData = {
    labels: tenure.map((d) => d.label),
    datasets: [
      {
        label: 'Attrition Rate (%)',
        data: tenure.map((d) => d.rate || 0),
        backgroundColor: 'rgba(5, 150, 105, 0.8)',
        borderColor: '#059669',
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  // 8. Job & Environment Satisfaction Matrix
  const jobSat = (satisfaction && satisfaction.job_satisfaction) || [];
  const envSat = (satisfaction && (satisfaction.env_satisfaction || satisfaction.environment_satisfaction)) || [];
  const satLabels = jobSat.length > 0 ? jobSat.map(d => `Level ${d.label}`) : ['Level 1 (Low)', 'Level 2 (Medium)', 'Level 3 (High)', 'Level 4 (Very High)'];
  const satisfactionChartData = {
    labels: satLabels,
    datasets: [
      {
        label: 'Job Satisfaction Rate (%)',
        data: jobSat.map((d) => d.rate || 0),
        backgroundColor: 'rgba(16, 185, 129, 0.85)',
        borderRadius: 4,
      },
      {
        label: 'Env Satisfaction Rate (%)',
        data: envSat.map((d) => d.rate || 0),
        backgroundColor: 'rgba(52, 211, 153, 0.85)',
        borderRadius: 4,
      },
    ],
  };

  // 9. Business Travel Frequency
  const travelChartData = {
    labels: travel.map((d) => String(d?.label || '').replace(/_/g, ' ')),
    datasets: [
      {
        data: travel.map((d) => d.attrition ?? d.total ?? 0),
        backgroundColor: travel.map((_, i) => travelPalette[i % travelPalette.length]),
        borderColor: '#ffffff',
        borderWidth: 2,
      },
    ],
  };

  // 10. Stock Options Level
  const stockChartData = {
    labels: stock.map((d) => `Level ${d.label}`),
    datasets: [
      {
        label: 'Attrition Rate (%)',
        data: stock.map((d) => d.rate || 0),
        backgroundColor: stock.map((d) => (String(d.label) === '0' ? 'rgba(239, 68, 68, 0.85)' : 'rgba(16, 185, 129, 0.85)')),
        borderRadius: 4,
      },
    ],
  };

  // 11. Work-Life Balance Rating
  const wlbLabels = worklife.length > 0 ? worklife.map(d => `Level ${d.label}`) : ['1 (Bad)', '2 (Good)', '3 (Better)', '4 (Best)'];
  const worklifeChartData = {
    labels: wlbLabels,
    datasets: [
      {
        label: 'Attrition Rate (%)',
        data: worklife.map((d) => d.rate || 0),
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderRadius: 4,
      },
    ],
  };

  return (
    <>
      {/* ── Section 1: Overview & Demographics ── */}
      <div className="section-heading">
        <span style={{ fontSize: '1.2rem' }}>📊</span>
        <h2>Attrition Overview & Departmental Breakdown</h2>
        <div className="section-line"></div>
      </div>

      <section className="charts-grid">
        {/* Department Attrition */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Department Attrition Breakdown</h3>
            <span className="chart-pill green">By Headcount</span>
          </div>
          <div className="chart-canvas-wrap">
            <Doughnut
              data={deptChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                  legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14 } },
                },
              }}
            />
          </div>
        </div>

        {/* Job Role Flight Risk */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Job Role Flight Risk (% Left)</h3>
            <span className="chart-pill danger">Ranked Highest to Lowest</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={roleChartData}
              options={{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { ticks: { callback: (v) => `${v}%` }, grid: { display: false } },
                  y: { grid: { display: false } },
                },
                plugins: { legend: { display: false } },
              }}
            />
          </div>
        </div>

        {/* Age Band Demographics */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Age Band Demographics & Flight Risk</h3>
            <span className="chart-pill warning">18-25 Highest: 35.8%</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={ageChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: { title: { display: true, text: 'Departures' }, grid: { color: '#f1f5f9' } },
                  y1: {
                    position: 'right',
                    title: { display: true, text: 'Rate (%)' },
                    grid: { display: false },
                    ticks: { callback: (v) => `${v}%` },
                  },
                  x: { grid: { display: false } },
                },
                plugins: { legend: { position: 'top', labels: { boxWidth: 10 } } },
              }}
            />
          </div>
        </div>

        {/* Monthly Income Bands */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Monthly Income Bands vs Attrition</h3>
            <span className="chart-pill green">Compensation Impact</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={incomeChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { stacked: true, grid: { display: false } },
                  y: { stacked: true, grid: { color: '#f1f5f9' } },
                },
                plugins: { legend: { position: 'top', labels: { boxWidth: 10 } } },
              }}
            />
          </div>
        </div>
      </section>

      {/* ── Section 2: Key Risk Factors ── */}
      <div className="section-heading">
        <span style={{ fontSize: '1.2rem' }}>🔥</span>
        <h2>Key Risk Factors & Root-Cause Analytics</h2>
        <div className="section-line"></div>
      </div>

      <section className="charts-grid">
        {/* Top Contributing Risk Drivers (Full Width) */}
        <div className="chart-card full-width">
          <div className="chart-header">
            <div>
              <h3 className="chart-title">Top Contributing Risk Drivers (Attrition Delta Impact)</h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                Percentage point difference in attrition between high-risk and low-risk cohorts
              </p>
            </div>
            <span className="chart-pill danger">Critical Levers</span>
          </div>
          <div className="chart-canvas-wrap" style={{ height: '260px' }}>
            <Bar
              data={factorsChartData}
              options={{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { ticks: { callback: (v) => `+${v}pp` }, grid: { color: '#f1f5f9' } },
                  y: { grid: { display: false } },
                },
                plugins: { legend: { display: false } },
              }}
            />
          </div>
        </div>

        {/* OverTime vs Standard Hours */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">OverTime vs Attrition Impact</h3>
            <span className="chart-pill danger">+20.1pp Gap</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={overtimeChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { grid: { display: false } },
                  y: { ticks: { callback: (v) => `${v}%` }, grid: { color: '#f1f5f9' } },
                },
                plugins: { legend: { display: false } },
              }}
            />
          </div>
        </div>

        {/* Tenure Band Breakdown */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Tenure & Early Career Flight Risk</h3>
            <span className="chart-pill warning">0-2 Years Critical</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={tenureChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { grid: { display: false } },
                  y: { ticks: { callback: (v) => `${v}%` }, grid: { color: '#f1f5f9' } },
                },
                plugins: { legend: { display: false } },
              }}
            />
          </div>
        </div>

        {/* Job & Environment Satisfaction */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Job & Environment Satisfaction</h3>
            <span className="chart-pill green">Morale Matrix (1-4)</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={satisfactionChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { grid: { display: false } },
                  y: { ticks: { callback: (v) => `${v}%` }, grid: { color: '#f1f5f9' } },
                },
                plugins: { legend: { position: 'top', labels: { boxWidth: 10 } } },
              }}
            />
          </div>
        </div>

        {/* Business Travel */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Business Travel Frequency Impact</h3>
            <span className="chart-pill warning">Travel Demands</span>
          </div>
          <div className="chart-canvas-wrap">
            <Doughnut
              data={travelChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: {
                  legend: { position: 'bottom', labels: { boxWidth: 10 } },
                },
              }}
            />
          </div>
        </div>

        {/* Stock Options */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Stock Option Retention Power</h3>
            <span className="chart-pill green">Equity Incentive</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={stockChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { grid: { display: false } },
                  y: { ticks: { callback: (v) => `${v}%` }, grid: { color: '#f1f5f9' } },
                },
                plugins: { legend: { display: false } },
              }}
            />
          </div>
        </div>

        {/* Work Life Balance */}
        <div className="chart-card">
          <div className="chart-header">
            <h3 className="chart-title">Work-Life Balance Rating Impact</h3>
            <span className="chart-pill green">Scale 1 (Bad) to 4 (Best)</span>
          </div>
          <div className="chart-canvas-wrap">
            <Bar
              data={worklifeChartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  x: { grid: { display: false } },
                  y: { ticks: { callback: (v) => `${v}%` }, grid: { color: '#f1f5f9' } },
                },
                plugins: { legend: { display: false } },
              }}
            />
          </div>
        </div>
      </section>
    </>
  );
}
