/**
 * Dashboard Filters Manager
 * Handles multi-dimensional interactive filtering and tags
 */

const Filters = {
  currentFilters: {},

  async init() {
    try {
      const opts = await API.getFilterOptions();
      this.populateRoleOptions(opts.job_roles || []);
      this.setupEventListeners();
    } catch (e) {
      console.error('Failed to load filter options:', e);
    }
  },

  populateRoleOptions(roles) {
    const select = document.getElementById('filterRole');
    if (!select) return;

    roles.forEach(role => {
      const opt = document.createElement('option');
      opt.value = role;
      opt.textContent = role;
      select.appendChild(opt);
    });
  },

  setupEventListeners() {
    const selects = ['filterDept', 'filterOvertime', 'filterRole', 'filterAge', 'filterGender'];

    selects.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('change', () => this.onFilterChange());
      }
    });

    const resetBtn = document.getElementById('btnResetFilters');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetFilters());
    }
  },

  async onFilterChange() {
    const dept = document.getElementById('filterDept')?.value;
    const overtime = document.getElementById('filterOvertime')?.value;
    const role = document.getElementById('filterRole')?.value;
    const age = document.getElementById('filterAge')?.value;
    const gender = document.getElementById('filterGender')?.value;

    this.currentFilters = {};

    if (dept) this.currentFilters.department = dept;
    if (overtime) this.currentFilters.overtime = overtime;
    if (role) this.currentFilters.job_role = role;
    if (gender) this.currentFilters.gender = gender;

    if (age) {
      if (age === '18-25') {
        this.currentFilters.age_min = 18;
        this.currentFilters.age_max = 25;
      } else if (age === '26-35') {
        this.currentFilters.age_min = 26;
        this.currentFilters.age_max = 35;
      } else if (age === '36-45') {
        this.currentFilters.age_min = 36;
        this.currentFilters.age_max = 45;
      } else if (age === '46-55') {
        this.currentFilters.age_min = 46;
        this.currentFilters.age_max = 55;
      } else if (age === '56+') {
        this.currentFilters.age_min = 56;
        this.currentFilters.age_max = 99;
      }
    }

    this.renderFilterTags();
    await this.applyFilters();
  },

  renderFilterTags() {
    const container = document.getElementById('activeFilterTags');
    if (!container) return;

    container.innerHTML = '';
    const entries = Object.entries(this.currentFilters);

    if (entries.length === 0) return;

    entries.forEach(([key, val]) => {
      if (key === 'age_max') return; // Handled under age_min
      let label = `${key}: ${val}`;
      if (key === 'age_min') {
        label = `age: ${this.currentFilters.age_min}-${this.currentFilters.age_max}`;
      }

      const tag = document.createElement('div');
      tag.className = 'filter-tag';
      tag.innerHTML = `
        <span>${label}</span>
        <span class="remove-tag" data-key="${key}">&times;</span>
      `;

      tag.querySelector('.remove-tag').onclick = () => {
        if (key === 'age_min') {
          delete this.currentFilters.age_min;
          delete this.currentFilters.age_max;
          const ageSelect = document.getElementById('filterAge');
          if (ageSelect) ageSelect.value = '';
        } else {
          delete this.currentFilters[key];
          const selectId = key === 'department' ? 'filterDept' :
                           key === 'job_role' ? 'filterRole' :
                           key === 'overtime' ? 'filterOvertime' :
                           key === 'gender' ? 'filterGender' : null;
          if (selectId) {
            const el = document.getElementById(selectId);
            if (el) el.value = '';
          }
        }
        this.renderFilterTags();
        this.applyFilters();
      };

      container.appendChild(tag);
    });
  },

  async applyFilters() {
    try {
      const activeCount = Object.keys(this.currentFilters).length;

      if (activeCount === 0) {
        // Reload all baseline dashboard data
        if (window.loadAllDashboardData) {
          await window.loadAllDashboardData();
        }
        return;
      }

      const data = await API.getFiltered(this.currentFilters);

      if (data.kpis) {
        Dashboard.renderKPIs(data.kpis);
      }
      if (data.department) {
        Dashboard.renderDeptChart(data.department);
      }
      if (data.job_role) {
        Dashboard.renderRoleChart(data.job_role);
      }
      if (data.age) {
        Dashboard.renderAgeChart(data.age);
      }
      if (data.overtime) {
        Dashboard.renderOvertimeChart(data.overtime);
      }
      if (data.tenure) {
        Dashboard.renderTenureChart(data.tenure);
      }
    } catch (e) {
      console.error('Failed to apply filters:', e);
    }
  },

  async resetFilters() {
    ['filterDept', 'filterOvertime', 'filterRole', 'filterAge', 'filterGender'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    this.currentFilters = {};
    this.renderFilterTags();
    if (window.loadAllDashboardData) {
      await window.loadAllDashboardData();
    }
  }
};
