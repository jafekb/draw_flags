import React, { useState } from "react";
import { searchByText, searchByImage } from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from "./SubmitDescriptionForm";
import ImageUploadForm from "./ImageUploadForm";

const FlagList = () => {
  const [flags, setFlags] = useState([]);
  const [searchMode, setSearchMode] = useState('text'); // 'text' or 'image'
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

  const searchModeStyle = {
    display: 'flex',
    marginBottom: '20px',
    backgroundColor: '#f0f0f0',
    borderRadius: '8px',
    padding: '4px'
  };

  const tabStyle = (isActive) => ({
    flex: 1,
    padding: '10px 20px',
    textAlign: 'center',
    backgroundColor: isActive ? '#007bff' : 'transparent',
    color: isActive ? 'white' : '#007bff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
    transition: 'all 0.3s ease'
  });

  return (
    <div>
      <h2>Find similar flags</h2>
      
      {/* Search mode selector */}
      <div style={searchModeStyle}>
        <button 
          style={tabStyle(searchMode === 'text')}
          onClick={() => setSearchMode('text')}
        >
          📝 Describe with words
        </button>
        <button 
          style={tabStyle(searchMode === 'image')}
          onClick={() => setSearchMode('image')}
        >
          🖼️ Upload an image
        </button>
      </div>

      {/* Search interface */}
      {searchMode === 'text' ? (
        <div>
          <h3>Describe the flag</h3>
          <SubmitDescriptionForm addFlag={handleTextSearch} />
        </div>
      ) : (
        <div>
          <h3>Upload a flag image</h3>
          <ImageUploadForm onImageUpload={handleImageSearch} />
        </div>
      )}

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
