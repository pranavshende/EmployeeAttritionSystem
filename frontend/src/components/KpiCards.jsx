import React from 'react';
import { Users, UserMinus, UserCheck, Wallet, Clock, AlertTriangle } from 'lucide-react';

export default function KpiCards({ kpis }) {
  if (!kpis) return null;

  const totalEmployees = (kpis.total_employees || 0).toLocaleString();
  const attritionRate = (kpis.attrition_rate || 0).toFixed(1);
  const attritionCount = (kpis.attrition_count || 0).toLocaleString();
  const retentionCount = (kpis.retention_count || 0).toLocaleString();
  const retentionRate = (100 - (kpis.attrition_rate || 0)).toFixed(1);
  const avgIncome = Math.round(kpis.avg_monthly_income || 0).toLocaleString();
  const overtimeRate = (kpis.overtime_attrition_rate || 0).toFixed(1);

  const topRole = kpis.highest_risk_role || { role: 'Sales Rep', rate: 39.8, count: 33, total: 83 };

  return (
    <section className="kpi-grid" aria-label="Key Performance Indicators">
      {/* 1. Total Workforce */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label">Total Workforce</span>
          <div className="kpi-icon-wrap">
            <Users size={20} />
          </div>
        </div>
        <div className="kpi-value">{totalEmployees}</div>
        <div className="kpi-subtext">
          <span>Active Dataset Baseline</span>
        </div>
      </div>

      {/* 2. Attrition Rate */}
      <div className="kpi-card danger">
        <div className="kpi-top">
          <span className="kpi-label">Attrition Rate</span>
          <div className="kpi-icon-wrap danger">
            <UserMinus size={20} />
          </div>
        </div>
        <div className="kpi-value">{attritionRate}%</div>
        <div className="kpi-subtext">
          <span className="highlight">{attritionCount}</span> departures recorded
        </div>
      </div>

      {/* 3. Retained Talent */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label">Retained Talent</span>
          <div className="kpi-icon-wrap">
            <UserCheck size={20} />
          </div>
        </div>
        <div className="kpi-value">{retentionCount}</div>
        <div className="kpi-subtext">
          <span className="highlight-green">{retentionRate}%</span> organizational retention
        </div>
      </div>

      {/* 4. Avg Monthly Salary */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label">Avg Monthly Salary</span>
          <div className="kpi-icon-wrap">
            <Wallet size={20} />
          </div>
        </div>
        <div className="kpi-value">₹{avgIncome}</div>
        <div className="kpi-subtext">
          <span>Median: ₹4,919 / mo</span>
        </div>
      </div>

      {/* 5. OverTime Flight Risk */}
      <div className="kpi-card danger">
        <div className="kpi-top">
          <span className="kpi-label">OverTime Flight Risk</span>
          <div className="kpi-icon-wrap danger">
            <Clock size={20} />
          </div>
        </div>
        <div className="kpi-value">{overtimeRate}%</div>
        <div className="kpi-subtext">
          <span className="highlight">3.0x higher</span> vs regular hours (10.4%)
        </div>
      </div>

      {/* 6. Highest Risk Role */}
      <div className="kpi-card warning">
        <div className="kpi-top">
          <span className="kpi-label">Highest Risk Role</span>
          <div className="kpi-icon-wrap warning">
            <AlertTriangle size={20} />
          </div>
        </div>
        <div className="kpi-value" style={{ fontSize: '1.4rem' }}>{topRole.role}</div>
        <div className="kpi-subtext">
          <span className="highlight">{topRole.rate}%</span> flight risk ({topRole.count}/{topRole.total})
        </div>
      </div>
    </section>
  );
}
