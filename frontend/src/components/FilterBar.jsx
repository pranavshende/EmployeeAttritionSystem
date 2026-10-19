import React from 'react';
import { SlidersHorizontal, RotateCcw } from 'lucide-react';

export default function FilterBar({
  filterOptions = {},
  currentFilters = {},
  onFilterChange,
  onReset
}) {
  const roles = filterOptions.job_roles || [];

  const handleSelect = (key, val) => {
    onFilterChange(key, val);
  };

  const handleAgeSelect = (val) => {
    onFilterChange('age_band', val);
  };

  // Compute active tags
  const activeTags = [];
  if (currentFilters.department) activeTags.push({ key: 'department', label: `Dept: ${currentFilters.department}` });
  if (currentFilters.overtime) activeTags.push({ key: 'overtime', label: `OverTime: ${currentFilters.overtime}` });
  if (currentFilters.job_role) activeTags.push({ key: 'job_role', label: `Role: ${currentFilters.job_role}` });
  if (currentFilters.gender) activeTags.push({ key: 'gender', label: `Gender: ${currentFilters.gender}` });
  if (currentFilters.age_band) activeTags.push({ key: 'age_band', label: `Age: ${currentFilters.age_band}` });

  return (
    <>
      <section className="filter-card" aria-label="Interactive Filters">
        <div className="filter-title">
          <SlidersHorizontal size={16} />
          <span>Filters</span>
        </div>

        {/* Department */}
        <select
          className="filter-select"
          value={currentFilters.department || ''}
          onChange={(e) => handleSelect('department', e.target.value)}
          aria-label="Filter Department"
        >
          <option value="">All Departments</option>
          <option value="Sales">Sales</option>
          <option value="Research & Development">Research & Development</option>
          <option value="Human Resources">Human Resources</option>
        </select>

        {/* OverTime */}
        <select
          className="filter-select"
          value={currentFilters.overtime || ''}
          onChange={(e) => handleSelect('overtime', e.target.value)}
          aria-label="Filter OverTime"
        >
          <option value="">All OverTime</option>
          <option value="Yes">OverTime: Yes</option>
          <option value="No">OverTime: No</option>
        </select>

        {/* Job Role */}
        <select
          className="filter-select"
          value={currentFilters.job_role || ''}
          onChange={(e) => handleSelect('job_role', e.target.value)}
          aria-label="Filter Job Role"
        >
          <option value="">All Job Roles</option>
          {roles.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>

        {/* Age Band */}
        <select
          className="filter-select"
          value={currentFilters.age_band || ''}
          onChange={(e) => handleAgeSelect(e.target.value)}
          aria-label="Filter Age Band"
        >
          <option value="">All Age Bands</option>
          <option value="18-25">18 - 25</option>
          <option value="26-35">26 - 35</option>
          <option value="36-45">36 - 45</option>
          <option value="46-55">46 - 55</option>
          <option value="56+">56+</option>
        </select>

        {/* Gender */}
        <select
          className="filter-select"
          value={currentFilters.gender || ''}
          onChange={(e) => handleSelect('gender', e.target.value)}
          aria-label="Filter Gender"
        >
          <option value="">All Genders</option>
          <option value="Male">Male</option>
          <option value="Female">Female</option>
        </select>

        {/* Reset Button */}
        <button className="btn-reset" onClick={onReset} title="Reset all filters">
          <RotateCcw size={14} />
          <span>Reset</span>
        </button>
      </section>

      {/* Active Filter Chips */}
      {activeTags.length > 0 && (
        <div className="active-filter-tags">
          {activeTags.map((tag) => (
            <div key={tag.key} className="active-tag">
              <span>{tag.label}</span>
              <span
                className="tag-remove"
                onClick={() => onFilterChange(tag.key, '')}
                title="Remove filter"
              >
                &times;
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
