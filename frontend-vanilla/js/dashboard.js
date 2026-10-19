/**
 * Dashboard Visualizations and KPI Manager
 * Uses Chart.js with custom Dark Mode Glassmorphism Theme
 */

const Dashboard = {
  charts: {},

  initTheme() {
    if (!window.Chart) return;
    Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.05)';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 21, 53, 0.95)';
    Chart.defaults.plugins.tooltip.titleColor = '#ffffff';
    Chart.defaults.plugins.tooltip.bodyColor = '#e2e8f0';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.15)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
  },

  destroyChart(id) {
    if (this.charts[id]) {
      this.charts[id].destroy();
      delete this.charts[id];
    }
  },

  renderKPIs(kpis) {
    if (!kpis) return;
    const el = (id) => document.getElementById(id);

    if (el('kpiTotalEmployees')) el('kpiTotalEmployees').textContent = (kpis.total_employees || 0).toLocaleString();
    if (el('kpiAttritionRate')) el('kpiAttritionRate').textContent = `${(kpis.attrition_rate || 0).toFixed(1)}%`;
    if (el('kpiAttritionCount')) el('kpiAttritionCount').textContent = (kpis.attrition_count || 0).toLocaleString();
    if (el('kpiRetentionCount')) el('kpiRetentionCount').textContent = (kpis.retention_count || 0).toLocaleString();
    if (el('kpiRetentionRate')) {
      const retRate = 100 - (kpis.attrition_rate || 0);
      el('kpiRetentionRate').textContent = `${retRate.toFixed(1)}%`;
    }
    if (el('kpiAvgIncome')) el('kpiAvgIncome').textContent = `₹${Math.round(kpis.avg_monthly_income || 0).toLocaleString()}`;
    if (el('kpiOvertimeRate')) el('kpiOvertimeRate').textContent = `${(kpis.overtime_attrition_rate || 0).toFixed(1)}%`;

    if (kpis.highest_risk_role) {
      if (el('kpiTopRiskRole')) el('kpiTopRiskRole').textContent = kpis.highest_risk_role.role;
      if (el('kpiTopRiskRoleRate')) el('kpiTopRiskRoleRate').textContent = `${kpis.highest_risk_role.rate}%`;
    }
  },

  renderDeptChart(data) {
    this.destroyChart('deptChart');
    const ctx = document.getElementById('deptChart');
    if (!ctx || !data) return;

    const labels = data.map(d => d.label);
    const attritions = data.map(d => d.attrition);
    const rates = data.map(d => d.rate);

    this.charts['deptChart'] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: attritions,
          backgroundColor: ['#00d4ff', '#7c3aed', '#f59e0b'],
          borderColor: '#0f1535',
          borderWidth: 2,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 12, padding: 15, color: '#e2e8f0' }
          },
          tooltip: {
            callbacks: {
              label(context) {
                const item = data[context.dataIndex];
                return ` ${item.label}: ${item.attrition} left (${item.rate}% rate, ${item.total} total)`;
              }
            }
          }
        },
        cutout: '65%'
      }
    });
  },

  renderRoleChart(data) {
    this.destroyChart('roleChart');
    const ctx = document.getElementById('roleChart');
    if (!ctx || !data) return;

    // Sort descending by rate
    const sorted = [...data].sort((a, b) => b.rate - a.rate);
    const labels = sorted.map(d => d.label);
    const rates = sorted.map(d => d.rate);

    this.charts['roleChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Attrition Rate (%)',
          data: rates,
          backgroundColor: rates.map(r => r > 25 ? 'rgba(239, 68, 68, 0.8)' : r > 15 ? 'rgba(245, 158, 11, 0.8)' : 'rgba(0, 212, 255, 0.8)'),
          borderColor: rates.map(r => r > 25 ? '#ef4444' : r > 15 ? '#f59e0b' : '#00d4ff'),
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            grid: { display: false },
            ticks: { callback: v => `${v}%` }
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 10 } }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel(context) {
                const item = sorted[context.dataIndex];
                return `Count: ${item.attrition} / ${item.total} employees`;
              }
            }
          }
        }
      }
    });
  },

  renderAgeChart(data) {
    this.destroyChart('ageChart');
    const ctx = document.getElementById('ageChart');
    if (!ctx || !data) return;

    this.charts['ageChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [
          {
            type: 'bar',
            label: 'Attrition Count',
            data: data.map(d => d.attrition),
            backgroundColor: 'rgba(239, 68, 68, 0.7)',
            borderRadius: 4,
            yAxisID: 'y'
          },
          {
            type: 'line',
            label: 'Attrition Rate (%)',
            data: data.map(d => d.rate),
            borderColor: '#00d4ff',
            backgroundColor: '#00d4ff',
            borderWidth: 2,
            pointRadius: 4,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            title: { display: true, text: 'Departures', font: { size: 10 } },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          },
          y1: {
            position: 'right',
            title: { display: true, text: 'Rate (%)', font: { size: 10 } },
            grid: { display: false },
            ticks: { callback: v => `${v}%` }
          }
        },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 10, padding: 10 } }
        }
      }
    });
  },

  renderIncomeChart(data) {
    this.destroyChart('incomeChart');
    const ctx = document.getElementById('incomeChart');
    if (!ctx || !data) return;

    this.charts['incomeChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [
          {
            label: 'Retained',
            data: data.map(d => d.retention),
            backgroundColor: 'rgba(16, 185, 129, 0.7)',
            borderRadius: 4
          },
          {
            label: 'Attrited',
            data: data.map(d => d.attrition),
            backgroundColor: 'rgba(239, 68, 68, 0.8)',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, grid: { color: 'rgba(255, 255, 255, 0.04)' } }
        },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 10, padding: 10 } },
          tooltip: {
            callbacks: {
              afterBody(items) {
                const idx = items[0].dataIndex;
                const item = data[idx];
                return `Attrition Rate: ${item.rate}%`;
              }
            }
          }
        }
      }
    });
  },

  renderFactorsChart(data) {
    this.destroyChart('factorsChart');
    const ctx = document.getElementById('factorsChart');
    if (!ctx || !data) return;

    const labels = data.map(d => `${d.factor} (${d.high_risk_cohort} vs ${d.low_risk_cohort})`);
    const impacts = data.map(d => d.impact_pp);

    this.charts['factorsChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Attrition Delta (+pp)',
          data: impacts,
          backgroundColor: impacts.map((_, i) => i === 0 ? 'rgba(239, 68, 68, 0.9)' : 'rgba(124, 58, 237, 0.85)'),
          borderColor: impacts.map((_, i) => i === 0 ? '#ef4444' : '#7c3aed'),
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { display: true, text: 'Risk Delta (Percentage Points Increase)', font: { size: 11 } },
            ticks: { callback: v => `+${v}pp` },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          },
          y: {
            grid: { display: false },
            ticks: { font: { size: 11, weight: '500' } }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(context) {
                const item = data[context.dataIndex];
                return ` +${item.impact_pp}pp delta (${item.high_risk_rate}% in ${item.high_risk_cohort} vs ${item.low_risk_rate}% in ${item.low_risk_cohort})`;
              }
            }
          }
        }
      }
    });
  },

  renderOvertimeChart(data) {
    this.destroyChart('overtimeChart');
    const ctx = document.getElementById('overtimeChart');
    if (!ctx || !data) return;

    this.charts['overtimeChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => `OverTime: ${d.label}`),
        datasets: [{
          label: 'Attrition Rate (%)',
          data: data.map(d => d.rate),
          backgroundColor: data.map(d => d.label === 'Yes' ? 'rgba(239, 68, 68, 0.8)' : 'rgba(16, 185, 129, 0.8)'),
          borderColor: data.map(d => d.label === 'Yes' ? '#ef4444' : '#10b981'),
          borderWidth: 1,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: { callback: v => `${v}%` },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel(context) {
                const item = data[context.dataIndex];
                return `${item.attrition} left out of ${item.total} employees`;
              }
            }
          }
        }
      }
    });
  },

  renderTenureChart(data) {
    this.destroyChart('tenureChart');
    const ctx = document.getElementById('tenureChart');
    if (!ctx || !data) return;

    this.charts['tenureChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [{
          label: 'Attrition Rate (%)',
          data: data.map(d => d.rate),
          backgroundColor: 'rgba(0, 212, 255, 0.7)',
          borderColor: '#00d4ff',
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: { callback: v => `${v}%` },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel(context) {
                const item = data[context.dataIndex];
                return `Departures: ${item.attrition}/${item.total}`;
              }
            }
          }
        }
      }
    });
  },

  renderSatisfactionChart(data) {
    this.destroyChart('satisfactionChart');
    const ctx = document.getElementById('satisfactionChart');
    if (!ctx || !data) return;

    const jobSat = data.job_satisfaction || [];
    const envSat = data.environment_satisfaction || [];

    this.charts['satisfactionChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Level 1 (Low)', 'Level 2 (Medium)', 'Level 3 (High)', 'Level 4 (Very High)'],
        datasets: [
          {
            label: 'Job Satisfaction Rate (%)',
            data: jobSat.map(d => d.rate),
            backgroundColor: 'rgba(124, 58, 237, 0.8)',
            borderRadius: 4
          },
          {
            label: 'Env Satisfaction Rate (%)',
            data: envSat.map(d => d.rate),
            backgroundColor: 'rgba(0, 212, 255, 0.8)',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: { callback: v => `${v}%` },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          }
        },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 10, padding: 10 } }
        }
      }
    });
  },

  renderTravelChart(data) {
    this.destroyChart('travelChart');
    const ctx = document.getElementById('travelChart');
    if (!ctx || !data) return;

    this.charts['travelChart'] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map(d => d.label.replace('_', ' ')),
        datasets: [{
          data: data.map(d => d.attrition),
          backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
          borderColor: '#0f1535',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 10, padding: 10 } },
          tooltip: {
            callbacks: {
              label(context) {
                const item = data[context.dataIndex];
                return ` ${item.label}: ${item.attrition} left (${item.rate}% rate)`;
              }
            }
          }
        },
        cutout: '60%'
      }
    });
  },

  renderStockChart(data) {
    this.destroyChart('stockChart');
    const ctx = document.getElementById('stockChart');
    if (!ctx || !data) return;

    this.charts['stockChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => `Level ${d.label}`),
        datasets: [{
          label: 'Attrition Rate (%)',
          data: data.map(d => d.rate),
          backgroundColor: data.map(d => d.label === '0' ? 'rgba(239, 68, 68, 0.8)' : 'rgba(16, 185, 129, 0.8)'),
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: { callback: v => `${v}%` },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              afterLabel(context) {
                const item = data[context.dataIndex];
                return `Departures: ${item.attrition} / ${item.total}`;
              }
            }
          }
        }
      }
    });
  },

  renderWorklifeChart(data) {
    this.destroyChart('worklifeChart');
    const ctx = document.getElementById('worklifeChart');
    if (!ctx || !data) return;

    this.charts['worklifeChart'] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['1 (Bad)', '2 (Good)', '3 (Better)', '4 (Best)'],
        datasets: [{
          label: 'Attrition Rate (%)',
          data: data.map(d => d.rate),
          backgroundColor: 'rgba(59, 130, 246, 0.8)',
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: { callback: v => `${v}%` },
            grid: { color: 'rgba(255, 255, 255, 0.04)' }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  },

  renderHighRiskTable(res) {
    const tbody = document.getElementById('highRiskTableBody');
    const countText = document.getElementById('highRiskCountText');
    const info = document.getElementById('paginationInfo');
    const controls = document.getElementById('paginationControls');

    if (!tbody || !res) return;

    const employees = res.employees || [];
    const totalCount = res.total_count || 0;
    const page = res.page || 1;
    const perPage = res.per_page || 20;
    const totalPages = res.total_pages || 1;

    if (countText) {
      countText.textContent = `Displaying ${totalCount} prioritized profiles exceeding flight risk thresholds`;
    }

    if (info) {
      const start = totalCount === 0 ? 0 : (page - 1) * perPage + 1;
      const end = Math.min(page * perPage, totalCount);
      info.textContent = `Showing ${start}-${end} of ${totalCount}`;
    }

    if (employees.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center" style="padding: 30px; color: var(--text-muted);">No employees found matching current criteria</td></tr>`;
      if (controls) controls.innerHTML = '';
      return;
    }

    tbody.innerHTML = employees.map(emp => {
      const riskClass = emp.risk_level === 'high' ? 'high' : emp.risk_level === 'medium' ? 'medium' : 'low';
      const attrClass = emp.attrition === 'Yes' ? 'yes' : 'no';
      const factorsText = (emp.matched_factors || []).join(', ') || 'N/A';

      return `
        <tr>
          <td><span class="font-mono">#${emp.employee_number}</span></td>
          <td>${emp.age}</td>
          <td>${emp.department}</td>
          <td>${emp.job_role}</td>
          <td>₹${Number(emp.monthly_income).toLocaleString()}</td>
          <td><span style="color: ${emp.overtime === 'Yes' ? 'var(--danger)' : 'var(--text-secondary)'}; font-weight: 600;">${emp.overtime}</span></td>
          <td>${emp.years_at_company} yrs</td>
          <td style="max-width: 250px; white-space: normal; font-size: 0.75rem; color: var(--text-secondary);">${factorsText}</td>
          <td><span class="risk-badge ${riskClass}">${emp.risk_score}/8 ${emp.risk_level}</span></td>
          <td><span class="attrition-badge ${attrClass}">${emp.attrition === 'Yes' ? 'Departed' : 'Retained'}</span></td>
        </tr>
      `;
    }).join('');

    // Pagination controls
    if (controls) {
      controls.innerHTML = `
        <button class="pagination-btn" id="btnPrevPage" ${page <= 1 ? 'disabled' : ''}>&larr; Prev</button>
        <span style="font-size: 0.8rem; padding: 6px 12px; color: var(--text-secondary);">Page ${page} of ${totalPages}</span>
        <button class="pagination-btn" id="btnNextPage" ${page >= totalPages ? 'disabled' : ''}>Next &rarr;</button>
      `;

      const prevBtn = document.getElementById('btnPrevPage');
      const nextBtn = document.getElementById('btnNextPage');

      if (prevBtn) {
        prevBtn.onclick = () => {
          if (page > 1 && window.loadHighRiskPage) window.loadHighRiskPage(page - 1);
        };
      }
      if (nextBtn) {
        nextBtn.onclick = () => {
          if (page < totalPages && window.loadHighRiskPage) window.loadHighRiskPage(page + 1);
        };
      }
    }
  }
};
