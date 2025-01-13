import React from "react";
import "./ImageGrid.css";
const ImageGrid = ({ images, title }) => {
    return (
        <div>
            {title && <h2 className="grid-title">{title}</h2>}
            <div className="grid-container">
                {images.map((image, index) => (
                    <div className="grid-item" key={index}>
                        <img src={image.wikipedia_image_url} alt={image.wikipedia_image_url} />
                        <p>{image.name + ": " + image.score.toFixed(3)}</p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ImageGrid;


