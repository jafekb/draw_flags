import React, { useMemo, useState } from "react";
import api from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from "./SubmitDescriptionForm";
import "./Flags.css";

const COLOR_OPTIONS = [
  "black",
  "white",
  "gray",
  "red",
  "orange",
  "yellow",
  "green",
  "blue",
  "light_blue",
  "purple",
  "pink",
];

const COLOR_LABELS = {
  light_blue: "Light Blue",
};

const FlagList = () => {
  const [flags, setFlags] = useState([]);
  const [sortOrder, setSortOrder] = useState(null);
  const [colorFilter, setColorFilter] = useState(null);
  const [isLoadingAll, setIsLoadingAll] = useState(false);

  const addFlag = async (textQuery) => {
    try {
      const response = await api.post("/", { text_query: textQuery });
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  const showAllFlags = async () => {
    setIsLoadingAll(true);
    try {
      const response = await api.get("/flags/all");
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error fetching all flags", error);
    } finally {
      setIsLoadingAll(false);
    }
  };

  const toggleSort = (nextSort) => {
    setSortOrder((current) => (current === nextSort ? null : nextSort));
  };

  const toggleColor = (nextColor) => {
    setColorFilter((current) => (current === nextColor ? null : nextColor));
  };

  const displayFlags = useMemo(() => {
    let nextFlags = [...flags];

    if (colorFilter) {
      nextFlags = nextFlags.filter(
        (flag) =>
          flag.color_coverage && flag.color_coverage[colorFilter] != null,
      );
    }

    if (sortOrder) {
      nextFlags.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      if (sortOrder === "za") {
        nextFlags.reverse();
      }
    }

    return nextFlags;
  }, [flags, sortOrder, colorFilter]);

  const handleClear = () => {
    setFlags([]);
    setSortOrder(null);
    setColorFilter(null);
  };

  return (
    <div>
      <SubmitDescriptionForm addFlag={addFlag} />
      <div className="or-divider">OR</div>
      <div className="show-all-controls">
        <button
          className="show-all-button"
          type="button"
          onClick={showAllFlags}
          disabled={isLoadingAll}
        >
          {isLoadingAll ? "Loading..." : "Show All"}
        </button>
        <div className="filter-options">
          <button
            className={`option-button ${sortOrder === "az" ? "active" : ""}`}
            type="button"
            onClick={() => toggleSort("az")}
          >
            A-Z
          </button>
          <button
            className={`option-button ${sortOrder === "za" ? "active" : ""}`}
            type="button"
            onClick={() => toggleSort("za")}
          >
            Z-A
          </button>
          {COLOR_OPTIONS.map((color) => (
            <button
              key={color}
              className={`option-button ${colorFilter === color ? "active" : ""}`}
              type="button"
              onClick={() => toggleColor(color)}
            >
              {COLOR_LABELS[color] || color.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {flags.length === 0 ? null : (
        <>
          <button
            onClick={handleClear}
            style={{ backgroundColor: "#FFCECE", color: "black" }}
          >
            Clear
          </button>
          <ImageGrid images={displayFlags} />
        </>
      )}
    </div>
  );
};

export default FlagList;
