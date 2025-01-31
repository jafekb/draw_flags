import React from "react";
import "./ImageGrid.css";
const ImageGrid = ({ images, title }) => {
    console.log({images})
  return (
    <div>
      {title && <h2 className="grid-title">{title}</h2>}
      <div className="grid-container">
        {images.map((image, index) => (
          <div className="grid-item" key={index}>
            <img
              src={image.wikipedia_image_url}
              alt={image.wikipedia_image_url}
            />

            <div className="flag-info">
                <a href={image.wikipedia_url} target="_blank">
                {image.name}
                </a>{" "}
                <p>({(image.score * 100).toFixed(1)}%)</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ImageGrid;
