import React, { useState } from 'react';

const ImageUploadForm = ({ onImageUpload }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = (file) => {
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      onImageUpload(file);
    } else {
      alert('Please select an image file (PNG, JPEG, etc.)');
    }
  };

  const handleFileInput = (event) => {
    const file = event.target.files[0];
    handleFileSelect(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const file = event.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  return (
    <div>
      <div
        className={`image-upload-area ${dragOver ? 'drag-over' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        style={{
          border: `2px dashed ${dragOver ? '#007bff' : '#ccc'}`,
          borderRadius: '8px',
          padding: '20px',
          textAlign: 'center',
          margin: '10px 0',
          backgroundColor: dragOver ? '#f0f8ff' : '#fafafa',
          transition: 'all 0.3s ease'
        }}
      >
        {selectedFile ? (
          <div>
            <p>✅ Selected: {selectedFile.name}</p>
            <img 
              src={URL.createObjectURL(selectedFile)} 
              alt="Selected flag" 
              style={{ 
                maxWidth: '200px', 
                maxHeight: '150px', 
                objectFit: 'contain',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            />
          </div>
        ) : (
          <div>
            <p>📤 Drop an image here or click to upload</p>
            <p style={{ fontSize: '0.9em', color: '#666' }}>
              Supports PNG, JPEG, GIF, etc.
            </p>
          </div>
        )}
      </div>
      
      <input
        type="file"
        accept="image/*"
        onChange={handleFileInput}
        style={{ display: 'none' }}
        id="image-upload-input"
      />
      
      <label 
        htmlFor="image-upload-input" 
        style={{
          display: 'inline-block',
          padding: '10px 20px',
          backgroundColor: '#007bff',
          color: 'white',
          borderRadius: '4px',
          cursor: 'pointer',
          border: 'none'
        }}
      >
        Choose File
      </label>
      
      {selectedFile && (
        <button
          onClick={() => setSelectedFile(null)}
          style={{
            marginLeft: '10px',
            padding: '10px 20px',
            backgroundColor: '#dc3545',
            color: 'white',
            borderRadius: '4px',
            cursor: 'pointer',
            border: 'none'
          }}
        >
          Clear
        </button>
      )}
    </div>
  );
};

export default ImageUploadForm;
