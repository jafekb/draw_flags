import React, { useMemo, useState } from "react";
import api from "../api.js";
import ImageGrid from "./ImageGrid";
import ImageSearchForm from "./ImageSearchForm";
import SubmitDescriptionForm from "./SubmitDescriptionForm";
import "./Flags.css";

const COLOR_OPTIONS = [
  "black",
  "white",
  "gray",
  "brown",
  "red",
  "orange",
  "gold",
  "yellow",
  "green",
  "blue",
  "light_blue",
  "purple",
  "pink",
];

const COLOR_THRESHOLD = 0.0005;

const COLOR_LABELS = {
  light_blue: "light blue",
};

const FlagList = () => {
  const [flags, setFlags] = useState([]);
  const [sortOrder, setSortOrder] = useState(null);
  const [colorFilter, setColorFilter] = useState(null);
  const [randomSeed, setRandomSeed] = useState(0);
  const [detected, setDetected] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState(null);
  const addFlag = async (textQuery) => {
    try {
      const response = await api.post("/", { text_query: textQuery });
      setDetected(null);
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  const searchByImage = async (imageDataUri) => {
    setImageLoading(true);
    setImageError(null);
    try {
      const response = await api.post("/image", { image: imageDataUri });
      setDetected(response.data.detected);
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error identifying flag from image", error);
      setImageError(
        error.response?.data?.detail ||
          "Couldn't identify a flag in that image. Please try another.",
      );
    } finally {
      setImageLoading(false);
    }
  };

  const showAllFlags = async () => {
    try {
      const response = await api.get("/flags/all");
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error fetching all flags", error);
    }
  };

  const ensureAllFlags = async () => {
    if (flags.length > 0) {
      return true;
    }
    await showAllFlags();
    return true;
  };

  const toggleSort = async (nextSort) => {
    await ensureAllFlags();
    setColorFilter(null);
    if (nextSort === "random") {
      setSortOrder("random");
      setRandomSeed((seed) => seed + 1);
      return;
    }
    setSortOrder((current) => (current === nextSort ? null : nextSort));
  };

  const toggleColor = async (nextColor) => {
    await ensureAllFlags();
    setSortOrder(null);
    setColorFilter((current) => (current === nextColor ? null : nextColor));
  };

  const displayFlags = useMemo(() => {
    let nextFlags = [...flags];

    if (colorFilter) {
      nextFlags = nextFlags.filter((flag) => {
        const coverage = flag.color_coverage?.[colorFilter];
        return typeof coverage === "number" && coverage >= COLOR_THRESHOLD;
      });
      nextFlags.sort((a, b) => {
        const aCoverage = a.color_coverage?.[colorFilter] ?? 0;
        const bCoverage = b.color_coverage?.[colorFilter] ?? 0;
        return bCoverage - aCoverage;
      });
      return nextFlags;
    }

    const createRng = (seed) => {
      let state = seed || 1;
      return () => {
        state |= 0;
        state = (state + 0x6d2b79f5) | 0;
        let t = Math.imul(state ^ (state >>> 15), 1 | state);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    };

    if (sortOrder) {
      if (sortOrder === "random") {
        const rng = createRng(randomSeed);
        for (let i = nextFlags.length - 1; i > 0; i -= 1) {
          const j = Math.floor(rng() * (i + 1));
          [nextFlags[i], nextFlags[j]] = [nextFlags[j], nextFlags[i]];
        }
        return nextFlags;
      }
      nextFlags.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      if (sortOrder === "za") {
        nextFlags.reverse();
      }
    }

    return nextFlags;
  }, [flags, sortOrder, colorFilter, randomSeed]);

  const handleClear = () => {
    setFlags([]);
    setSortOrder(null);
    setColorFilter(null);
    setDetected(null);
    setImageError(null);
  };

  return (
    <div>
      <SubmitDescriptionForm addFlag={addFlag} />
      <div className="or-divider">OR</div>
      <ImageSearchForm
        onSubmit={searchByImage}
        loading={imageLoading}
        error={imageError}
      />
      <div className="or-divider">OR</div>
      <div className="show-all-controls">
        <span className="show-all-label">Show All:</span>
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
          <button
            className={`option-button ${sortOrder === "random" ? "active" : ""}`}
            type="button"
            onClick={() => toggleSort("random")}
          >
            Random
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
          {detected && (
            <p className="image-search__detected">Detected: {detected}</p>
          )}
          <ImageGrid images={displayFlags} coverageColor={colorFilter} />
        </>
      )}
    </div>
  );
};

export default FlagList;
