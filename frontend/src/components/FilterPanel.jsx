import React, { useState } from "react";
import "./FilterPanel.css";

const FilterPanel = ({ onFilterChange, activeFilters }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState({
    categories: [],
    continent: "",
    country: "",
  });

  const continents = [
    "Africa",
    "Antarctica",
    "Asia",
    "Europe",
    "North America",
    "Oceania",
    "South America",
  ];

  // Common countries (can be expanded)
  const countries = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Argentina", "Armenia",
    "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados",
    "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina",
    "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia",
    "Cameroon", "Canada", "Cape Verde", "Central African Republic", "Chad", "Chile",
    "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus",
    "Czech Republic", "Democratic Republic of the Congo", "Denmark", "Djibouti", "Dominica",
    "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea",
    "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia",
    "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau",
    "Guyana", "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran",
    "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia",
    "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
    "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands",
    "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia",
    "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal",
    "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea",
    "North Macedonia", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama",
    "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
    "Romania", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe",
    "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore",
    "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea",
    "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland",
    "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo",
    "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
    "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen",
    "Zambia", "Zimbabwe"
  ];

  const handleCategoryToggle = (category) => {
    setLocalFilters((prev) => {
      const categories = prev.categories.includes(category)
        ? prev.categories.filter((c) => c !== category)
        : [...prev.categories, category];
      return { ...prev, categories };
    });
  };

  const handleContinentChange = (e) => {
    setLocalFilters((prev) => ({ ...prev, continent: e.target.value }));
  };

  const handleCountryChange = (e) => {
    setLocalFilters((prev) => ({ ...prev, country: e.target.value }));
  };

  const applyFilters = () => {
    // Convert empty strings to null for API
    const filtersToApply = {
      categories: localFilters.categories.length > 0 ? localFilters.categories : null,
      continent: localFilters.continent || null,
      country: localFilters.country || null,
    };
    onFilterChange(filtersToApply);
  };

  const clearFilters = () => {
    setLocalFilters({
      categories: [],
      continent: "",
      country: "",
    });
    onFilterChange({
      categories: null,
      continent: null,
      country: null,
    });
  };

  const hasActiveFilters =
    localFilters.categories.length > 0 ||
    localFilters.continent !== "" ||
    localFilters.country !== "";

  return (
    <div className="filter-panel">
      <div className="filter-header">
        <button
          className="filter-toggle"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? "▼" : "▶"} Filters
          {hasActiveFilters && <span className="filter-badge">●</span>}
        </button>
        {hasActiveFilters && (
          <button className="clear-filters-btn" onClick={clearFilters}>
            Clear All
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="filter-content">
          {/* Category Filter */}
          <div className="filter-section">
            <label className="filter-label">Flag Type:</label>
            <div className="category-buttons">
              <button
                className={`category-btn ${
                  localFilters.categories.includes("national") ? "active" : ""
                }`}
                onClick={() => handleCategoryToggle("national")}
              >
                National
              </button>
              <button
                className={`category-btn ${
                  localFilters.categories.includes("subdivision") ? "active" : ""
                }`}
                onClick={() => handleCategoryToggle("subdivision")}
              >
                State/Province
              </button>
              <button
                className={`category-btn ${
                  localFilters.categories.includes("city") ? "active" : ""
                }`}
                onClick={() => handleCategoryToggle("city")}
              >
                City
              </button>
            </div>
          </div>

          {/* Continent Filter */}
          <div className="filter-section">
            <label className="filter-label" htmlFor="continent-select">
              Continent:
            </label>
            <select
              id="continent-select"
              className="filter-select"
              value={localFilters.continent}
              onChange={handleContinentChange}
            >
              <option value="">All Continents</option>
              {continents.map((continent) => (
                <option key={continent} value={continent}>
                  {continent}
                </option>
              ))}
            </select>
          </div>

          {/* Country Filter */}
          <div className="filter-section">
            <label className="filter-label" htmlFor="country-select">
              Country:
            </label>
            <select
              id="country-select"
              className="filter-select"
              value={localFilters.country}
              onChange={handleCountryChange}
            >
              <option value="">All Countries</option>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>

          <button className="apply-filters-btn" onClick={applyFilters}>
            Apply Filters
          </button>
        </div>
      )}

      {/* Active Filters Display */}
      {(activeFilters.categories ||
        activeFilters.continent ||
        activeFilters.country) && (
        <div className="active-filters">
          {activeFilters.categories && activeFilters.categories.length > 0 && (
            <div className="filter-chips">
              {activeFilters.categories.map((cat) => (
                <span key={cat} className="filter-chip">
                  {cat === "national"
                    ? "National"
                    : cat === "subdivision"
                    ? "State/Province"
                    : "City"}
                </span>
              ))}
            </div>
          )}
          {activeFilters.continent && (
            <span className="filter-chip">{activeFilters.continent}</span>
          )}
          {activeFilters.country && (
            <span className="filter-chip">{activeFilters.country}</span>
          )}
        </div>
      )}
    </div>
  );
};

export default FilterPanel;

