import React, { useEffect, useRef, useState } from "react";
import "./ImageGrid.css";

// Render the grid in windows so we never mount thousands of <img> at once — each
// image hotlinks Wikimedia, and firing all of them (e.g. "Show All" = ~2700) gets
// the browser rate-limited (429), which shows as blank flags. We reveal more as the
// user scrolls to the bottom.
const PAGE_SIZE = 60;

// Wikimedia serves rendered, CDN-cached PNG thumbnails at a /thumb/ path. They're
// lighter and far more cache-friendly than hotlinking raw SVG originals (which get
// rate-limited / occasionally fail), so we render thumbnails and fall back to the
// original URL on error. Width must be one of Wikimedia's allowed thumbnail sizes
// (arbitrary widths now 400). The grid displays flags at ~264px, so 500 keeps them
// crisp on 2x/Retina displays while staying far smaller than the source SVGs.
const THUMB_WIDTH = 500;

const thumbnailUrl = (url) => {
  try {
    const u = new URL(url);
    if (u.hostname !== "upload.wikimedia.org") return url;
    const parts = u.pathname.split("/"); // /wikipedia/<proj>/<h>/<hh>/<name>
    if (parts.includes("thumb") || parts.length < 6) return url;
    const name = parts[parts.length - 1];
    const hh = parts[parts.length - 2];
    const h = parts[parts.length - 3];
    const proj = parts.slice(1, parts.length - 3).join("/");
    const ext = name.split(".").pop().toLowerCase();
    let thumbName = `${THUMB_WIDTH}px-${name}`;
    if (ext === "svg" || ext === "svgz") thumbName += ".png";
    else if (ext === "tif" || ext === "tiff") thumbName += ".jpg";
    return `${u.origin}/${proj}/thumb/${h}/${hh}/${name}/${thumbName}`;
  } catch {
    return url;
  }
};

const formatCoverageLabel = (color) => {
  if (!color) {
    return "";
  }
  if (color === "light_blue") {
    return "light blue";
  }
  return color
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const ImageGrid = ({ images, title, coverageColor }) => {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const sentinelRef = useRef(null);

  // Reset the window whenever the image set changes (new search / sort / filter).
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [images]);

  // Reveal the next page when the sentinel scrolls into view.
  useEffect(() => {
    if (visibleCount >= images.length) {
      return undefined;
    }
    const node = sentinelRef.current;
    if (!node) {
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisibleCount((count) =>
            Math.min(count + PAGE_SIZE, images.length),
          );
        }
      },
      { rootMargin: "400px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [visibleCount, images.length]);

  const visibleImages = images.slice(0, visibleCount);

  return (
    <div>
      {title && <h2 className="grid-title">{title}</h2>}
      <div className="grid-container">
        {visibleImages.map((image, index) => {
          const coverageValue =
            coverageColor &&
            typeof image.color_coverage?.[coverageColor] === "number"
              ? image.color_coverage[coverageColor]
              : null;
          return (
            <div className="grid-item" key={index}>
              <a
                className="grid-item__link"
                href={image.wikipedia_url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={image.name || "Flag"}
              >
                <img
                  src={thumbnailUrl(image.wikipedia_image_url)}
                  alt={image.name || "Flag"}
                  loading="lazy"
                  onError={(e) => {
                    // First fall back from the thumbnail to the original file,
                    // then hide if that also fails.
                    if (
                      !e.target.dataset.fellBack &&
                      e.target.src !== image.wikipedia_image_url
                    ) {
                      e.target.dataset.fellBack = "1";
                      e.target.src = image.wikipedia_image_url;
                    } else {
                      e.target.style.display = "none";
                      e.target.parentElement.style.minHeight = "200px";
                    }
                  }}
                />
              </a>

              <div className="flag-info">
                <a
                  href={image.wikipedia_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {image.name}
                </a>{" "}
                {coverageValue !== null ? (
                  <p>
                    {formatCoverageLabel(coverageColor)}:{" "}
                    {(coverageValue * 100).toFixed(1)}%
                  </p>
                ) : (
                  typeof image.score === "number" && (
                    <p>({(image.score * 100).toFixed(1)}%)</p>
                  )
                )}
                {image.attribution && (
                  <p className="attribution">{image.attribution}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {visibleCount < images.length && (
        <div ref={sentinelRef} className="grid-sentinel" aria-hidden="true" />
      )}
    </div>
  );
};

export default ImageGrid;
