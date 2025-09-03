import React, { useState } from "react";
import { searchByText, searchByImage } from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from "./SubmitDescriptionForm";
import ImageUploadForm from "./ImageUploadForm";

const FlagList = () => {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleTextSearch = async (textQuery) => {
    setLoading(true);
    try {
      const response = await searchByText(textQuery);
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error searching by text", error);
      alert("Error searching by text. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleImageSearch = async (imageFile) => {
    setLoading(true);
    try {
      const response = await searchByImage(imageFile);
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error searching by image", error);
      alert("Error searching by image. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const containerStyle = {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    gap: '40px',
    margin: '30px 0',
    flexWrap: 'wrap'
  };

  const searchSectionStyle = {
    flex: '1',
    minWidth: '300px',
    maxWidth: '400px',
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  };

  const orStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '60px',
    height: '60px',
    backgroundColor: '#007bff',
    color: 'white',
    borderRadius: '50%',
    fontSize: '24px',
    fontWeight: 'bold',
    alignSelf: 'center',
    marginTop: '40px',
    flexShrink: 0
  };

  return (
    <div>
      <h2 style={{ textAlign: 'center', marginBottom: '10px' }}>Find similar flags</h2>
      <p style={{ textAlign: 'center', color: '#666', marginBottom: '30px' }}>
        Describe the flag in words or upload an image
      </p>
      
      {/* Side-by-side search interface */}
      <div style={containerStyle}>
        {/* Text search section */}
        <div style={searchSectionStyle}>
          <h3 style={{ textAlign: 'center', marginBottom: '20px', color: '#333' }}>
            📝 Describe with words
          </h3>
          <SubmitDescriptionForm addFlag={handleTextSearch} />
        </div>

        {/* OR separator */}
        <div style={orStyle}>
          OR
        </div>

        {/* Image search section */}
        <div style={searchSectionStyle}>
          <h3 style={{ textAlign: 'center', marginBottom: '20px', color: '#333' }}>
            🖼️ Upload an image
          </h3>
          <ImageUploadForm onImageUpload={handleImageSearch} />
        </div>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div style={{ textAlign: 'center', margin: '20px 0' }}>
          <p>🔍 Searching for similar flags...</p>
        </div>
      )}

      {/* Results */}
      {flags.length === 0 ? null : (
        <>
          <button
            onClick={() => setFlags([])}
            style={{ 
              backgroundColor: "#FFCECE", 
              color: "black",
              padding: "10px 20px",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
              margin: "10px 0"
            }}
          >
            Clear Results
          </button>
          <ImageGrid images={flags} title="Similar flags found:" />
        </>
      )}
    </div>
  );
};

export default FlagList;
