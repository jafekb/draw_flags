import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import "./FlagBanner.css";

const DEFAULT_LIMIT = 30;
const DEFAULT_REFRESH_INTERVAL_MS = 45000;

const FlagBanner = ({
  limit = DEFAULT_LIMIT,
  refreshIntervalMs = DEFAULT_REFRESH_INTERVAL_MS,
}) => {
  const [flags, setFlags] = useState([]);

  const fetchFlags = async () => {
    try {
      const response = await api.get("/flags/random", {
        params: { limit },
      });
      setFlags(response.data.flags || []);
    } catch (error) {
      console.error("Error fetching banner flags", error);
    }
  };

  useEffect(() => {
    fetchFlags();
    const intervalId = setInterval(fetchFlags, refreshIntervalMs);
    return () => clearInterval(intervalId);
  }, [limit, refreshIntervalMs]);

  const repeatedFlags = useMemo(() => {
    if (flags.length === 0) {
      return [];
    }
    return [...flags, ...flags];
  }, [flags]);

  if (repeatedFlags.length === 0) {
    return null;
  }

  return (
    <div className="flag-banner" aria-label="Random flag banner">
      <div className="flag-banner__track">
        {repeatedFlags.map((flag, index) => (
          <a
            key={`${flag.name}-${index}`}
            className="flag-banner__item"
            href={flag.wikipedia_url}
            target="_blank"
            rel="noreferrer"
            title={flag.name}
          >
            <img
              src={flag.wikipedia_image_url}
              alt={flag.name}
              loading="lazy"
            />
          </a>
        ))}
      </div>
    </div>
  );
};

export default FlagBanner;
