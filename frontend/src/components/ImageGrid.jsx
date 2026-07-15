import React from "react";
import "./ImageGrid.css";

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
  console.log({ images });
  return (
    <div>
      {title && <h2 className="grid-title">{title}</h2>}
      <div className="grid-container">
        {images.map((image, index) => {
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
                  src={image.wikipedia_image_url}
                  alt={image.name || "Flag"}
                  loading="lazy"
                  onError={(e) => {
                    e.target.style.display = "none";
                    e.target.parentElement.style.minHeight = "200px";
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
    </div>
  );
};

export default ImageGrid;
