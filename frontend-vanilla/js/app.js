/**
 * Main Application Bootstrap
 * Coordinates initialization of dashboard, charts, filters, and chatbot
 */

let currentHighRiskData = null;

async function loadAllDashboardData() {
  try {
    // 1. Load KPIs
    const kpis = await API.getKPIs();
    Dashboard.renderKPIs(kpis);

    // 2. Load and render all charts in parallel
    const [
      deptData,
      roleData,
      ageData,
      incomeData,
      factorsData,
      overtimeData,
      tenureData,
      satisfactionData,
      travelData,
      stockData,
      worklifeData
    ] = await Promise.all([
      API.getChart('department'),
      API.getChart('job-role'),
      API.getChart('age'),
      API.getChart('income'),
      API.getChart('factors'),
      API.getChart('overtime'),
      API.getChart('tenure'),
      API.getChart('satisfaction'),
      API.getChart('travel'),
      API.getChart('stock-options'),
      API.getChart('work-life-balance')
    ]);

    Dashboard.renderDeptChart(deptData);
    Dashboard.renderRoleChart(roleData);
    Dashboard.renderAgeChart(ageData);
    Dashboard.renderIncomeChart(incomeData);
    Dashboard.renderFactorsChart(factorsData);
    Dashboard.renderOvertimeChart(overtimeData);
    Dashboard.renderTenureChart(tenureData);
    Dashboard.renderSatisfactionChart(satisfactionData);
    Dashboard.renderTravelChart(travelData);
    Dashboard.renderStockChart(stockData);
    Dashboard.renderWorklifeChart(worklifeData);

    // 3. Load high-risk employees
    await loadHighRiskPage(1);

  } catch (err) {
    console.error('Error loading dashboard data:', err);
  }
}

async function loadHighRiskPage(page = 1) {
  try {
    const res = await API.getHighRisk(page, 15);
    currentHighRiskData = res;
    Dashboard.renderHighRiskTable(res);
  } catch (err) {
    console.error('Error loading high-risk watchlist:', err);
  }
}

function setupTableSearch() {
  const searchInput = document.getElementById('tableSearch');
  if (!searchInput) return;

  searchInput.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase().trim();
    if (!currentHighRiskData || !currentHighRiskData.employees) return;

    if (!term) {
      Dashboard.renderHighRiskTable(currentHighRiskData);
      return;
    }

    const filteredEmployees = currentHighRiskData.employees.filter(emp => {
      const matchId = String(emp.employee_number).toLowerCase().includes(term);
      const matchDept = String(emp.department).toLowerCase().includes(term);
      const matchRole = String(emp.job_role).toLowerCase().includes(term);
      const matchFactors = (emp.matched_factors || []).some(f => f.toLowerCase().includes(term));
      return matchId || matchDept || matchRole || matchFactors;
    });

    Dashboard.renderHighRiskTable({
      ...currentHighRiskData,
      employees: filteredEmployees,
      total_count: filteredEmployees.length
    });
  });
}

// Global hook for pagination and reset
window.loadHighRiskPage = loadHighRiskPage;
window.loadAllDashboardData = loadAllDashboardData;

// Bootstrap on DOM Ready
document.addEventListener('DOMContentLoaded', async () => {
  // 1. Initialize theme
  Dashboard.initTheme();

  // 2. Initialize Lucide icons
  if (window.lucide) {
    lucide.createIcons();
  }

  // 3. Initialize Chatbot
  Chatbot.init();

  // 4. Initialize Filters
  await Filters.init();

  // 5. Setup Watchlist search
  setupTableSearch();

  // 6. Load full dashboard analytics
  await loadAllDashboardData();

  // Re-run icons in case new elements rendered
  if (window.lucide) {
    lucide.createIcons();
  }
});
