import React, { useState } from 'react';
import { Search } from 'lucide-react';

export default function HighRiskTable({
  highRiskData = {},
  currentPage = 1,
  onPageChange,
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const employees = highRiskData.employees || [];
  const totalCount = highRiskData.total_count || 0;
  const totalPages = highRiskData.total_pages || 1;
  const perPage = highRiskData.per_page || 15;

  // Filter based on search input
  const filteredEmployees = employees.filter((emp) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase().trim();
    const matchId = String(emp.employee_number).toLowerCase().includes(term);
    const matchDept = String(emp.department).toLowerCase().includes(term);
    const matchRole = String(emp.job_role).toLowerCase().includes(term);
    const matchFactors = (emp.matched_factors || []).some((f) =>
      f.toLowerCase().includes(term)
    );
    return matchId || matchDept || matchRole || matchFactors;
  });

  const startRecord = totalCount === 0 ? 0 : (currentPage - 1) * perPage + 1;
  const endRecord = Math.min(currentPage * perPage, totalCount);

  return (
    <>
      <div className="section-heading">
        <span style={{ fontSize: '1.2rem' }}>⚠️</span>
        <h2>High-Risk Employee Watchlist & Early Warning</h2>
        <div className="section-line"></div>
      </div>

      <section className="table-card" aria-label="High Risk Watchlist">
        <div className="table-top">
          <div>
            <h3 className="chart-title">Employees with Cumulative Flight Risk (Score &ge; 4 / 8)</h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Displaying {totalCount} prioritized profiles exceeding flight risk thresholds
            </p>
          </div>
          <div style={{ position: 'relative' }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
              }}
            />
            <input
              type="text"
              className="search-input"
              style={{ paddingLeft: '34px' }}
              placeholder="Search ID, role, department..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Age</th>
                <th>Department</th>
                <th>Job Role</th>
                <th>Monthly Salary</th>
                <th>OverTime</th>
                <th>Tenure</th>
                <th>Flight Risk Factors</th>
                <th>Risk Score</th>
                <th>Attrition Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredEmployees.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    No employees found matching current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredEmployees.map((emp) => {
                  const riskClass =
                    emp.risk_level === 'high' ? 'high' : emp.risk_level === 'medium' ? 'medium' : 'low';
                  const factorsList = (emp.matched_factors || []).join(', ') || 'N/A';

                  return (
                    <tr key={emp.employee_number}>
                      <td>
                        <strong style={{ fontFamily: 'monospace' }}>#{emp.employee_number}</strong>
                      </td>
                      <td>{emp.age}</td>
                      <td>{emp.department}</td>
                      <td>{emp.job_role}</td>
                      <td>₹{Number(emp.monthly_income).toLocaleString()}</td>
                      <td>
                        <span
                          style={{
                            color: emp.overtime === 'Yes' ? 'var(--danger-text)' : 'var(--text-secondary)',
                            fontWeight: 700,
                          }}
                        >
                          {emp.overtime}
                        </span>
                      </td>
                      <td>{emp.years_at_company} yrs</td>
                      <td style={{ maxWidth: '260px', whiteSpace: 'normal', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {factorsList}
                      </td>
                      <td>
                        <span className={`badge-risk ${riskClass}`}>
                          {emp.risk_score}/8 {emp.risk_level}
                        </span>
                      </td>
                      <td>
                        <span className={`badge-attrition ${emp.attrition === 'Yes' ? 'yes' : 'no'}`}>
                          {emp.attrition === 'Yes' ? 'Departed' : 'Retained'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="table-foot">
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            Showing {startRecord}-{endRecord} of {totalCount} records
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              className="page-btn"
              disabled={currentPage <= 1}
              onClick={() => onPageChange(currentPage - 1)}
            >
              &larr; Prev
            </button>
            <span style={{ fontSize: '0.82rem', padding: '0 8px', color: 'var(--text-secondary)' }}>
              Page {currentPage} of {totalPages}
            </span>
            <button
              className="page-btn"
              disabled={currentPage >= totalPages}
              onClick={() => onPageChange(currentPage + 1)}
            >
              Next &rarr;
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
