import React, { useEffect, useState } from "react";
import api from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from "./SubmitDescriptionForm";
import FilterPanel from "./FilterPanel";

const FlagList = () => {
  const [flags, setFlags] = useState([]);
  const [filters, setFilters] = useState({
    categories: null,
    continent: null,
    country: null,
  });

  const addFlag = async (textQuery) => {
    try {
      const response = await api.post("/", {
        text_query: textQuery,
        categories: filters.categories,
        continent: filters.continent,
        country: filters.country,
      });
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    // Clear results when filters change so user knows to search again
    setFlags([]);
  };

  return (
    <div>
      <FilterPanel onFilterChange={handleFilterChange} activeFilters={filters} />
      
      <h2>Describe the flag using words</h2>
      <SubmitDescriptionForm addFlag={addFlag} />

      {flags.length === 0 ? null : (
        <>
          <button
            onClick={() => setFlags([])}
            style={{ backgroundColor: "#FFCECE", color: "black" }}
          >
            Clear
          </button>
          <ImageGrid images={flags} title="I bet it's..." />
        </>
      )}
    </div>
  );
};

export default FlagList;
