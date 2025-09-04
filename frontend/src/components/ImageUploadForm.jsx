import React, { useState } from "react";

const ImageUploadForm = ({ onImageUpload }) => {
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileInput = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith("image/")) {
      setSelectedFile(file);
      onImageUpload(file);
    } else {
      alert("Please select an image file (PNG, JPEG, etc.)");
    }
  };

  return (
    <div style={{ textAlign: "center" }}>
      {selectedFile && (
        <div style={{ marginBottom: "20px" }}>
          <p style={{ marginBottom: "10px" }}>
            ✅ Selected: {selectedFile.name}
          </p>
          <img
            src={URL.createObjectURL(selectedFile)}
            alt="Selected flag"
            style={{
              maxWidth: "200px",
              maxHeight: "150px",
              objectFit: "contain",
              border: "1px solid #ddd",
              borderRadius: "4px",
            }}
          />
        </div>
      )}

      <input
        type="file"
        accept="image/*"
        onChange={handleFileInput}
        style={{ display: "none" }}
        id="image-upload-input"
      />

      <label
        htmlFor="image-upload-input"
        style={{
          display: "inline-block",
          padding: "10px 20px",
          backgroundColor: "#007bff",
          color: "white",
          borderRadius: "4px",
          cursor: "pointer",
          border: "none",
          fontSize: "16px",
        }}
      >
        Choose File
      </label>

      {selectedFile && (
        <button
          onClick={() => setSelectedFile(null)}
          style={{
            marginLeft: "10px",
            padding: "10px 20px",
            backgroundColor: "#dc3545",
            color: "white",
            borderRadius: "4px",
            cursor: "pointer",
            border: "none",
            fontSize: "16px",
          }}
        >
          Clear
        </button>
      )}
    </div>
  );
};

export default ImageUploadForm;
