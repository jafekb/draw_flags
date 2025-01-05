import React, { useState } from "react";

const ImageUploader = ({ addImageUpload }) => {
    const [image, setImage] = useState(null);

    const handleImageChange = (event) => {
        event.preventDefault();

        const file = event.target.files[0];
        if (file) {
            const imageURL = URL.createObjectURL(file);
            // TODO(bjafek) figure out how to pass something better than
            //  this incomplete name
            addImageUpload(file.name);
            setImage(imageURL);
        }
    };

    return (
        <div style={{ textAlign: "center" }}>
            <h2>Upload an Image</h2>
            <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                style={{ marginBottom: "20px" }}
            />
            {image && (
                <div>
                    <h3>Preview:</h3>
                    <img
                        src={image}
                        alt="Preview"
                        style={{ maxWidth: "300px", borderRadius: "8px" }}
                    />
                </div>
            )}
        </div>
    );
};

export default ImageUploader;
