import React, { useEffect, useState } from 'react';
import api from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from './SubmitDescriptionForm';
import ImageUploader from './ImageUploader';

const FlagList = () => {
  const [flags, setTextFlags] = useState([]);
  const [image_flags, setImageFlags] = useState([]);

  const fetchFlags = async () => {
    try {
      const response = await api.get('/flags');
      // clear the image one when you ask for the text one
      setImageFlags([]);
      setTextFlags(response.data.flags);
    } catch (error) {
      console.error("Error fetching flags", error);
    }
  };

  const fetchImageFlags = async () => {
    try {
      const response = await api.get('/upload_image');
      // clear the text one when you ask for the image one
      setTextFlags([]);
      setImageFlags(response.data.flags);
    } catch (error) {
      console.error("Error fetching flags", error);
    }
  };

  const addFlag = async (textQuery) => {
    try {
      await api.post('/flags', { "text_query": textQuery });
      fetchFlags();  // Refresh the list after adding a flag
    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  const addImageUpload = async (imageData) => {
    try {
      await api.post('/upload_image', {data: imageData });
      fetchImageFlags();  // Refresh the list after adding a flag
    } catch (error) {
      console.error("Error adding image flag", error);
    }
  };

  const handleClick = () => {
    setTextFlags([]);
    setImageFlags([]);
  };

  useEffect(() => {
    fetchFlags();
    fetchImageFlags();
  }, []);

  // TODO(bjafek) this if statement is clumsy.
  // TODO(bjafek) don't know how to clear the image_flags one
  if (flags.length === 0 && image_flags.length === 0) {
      return (
        <div>
          <h2>Describe the flag using words</h2>
          <SubmitDescriptionForm addFlag={addFlag} />
          <h2>Or upload a picture</h2>
          <ImageUploader addImageUpload={addImageUpload} />
        </div>
      );
  } else if (image_flags.length === 0) {
      return (
        <div>
          <h2>Describe the flag using words</h2>
          <SubmitDescriptionForm addFlag={addFlag} />
          <h2>Or upload a picture</h2>
          <ImageUploader addImageUpload={addImageUpload} />
          // TODO(bjafek) consider making the ClearButton its own class
          <button
          onClick={handleClick}
          style={{ backgroundColor: '#FFCECE', color: 'black' }}
          >
            Clear
          </button>
          <ImageGrid images={flags} title="I bet it's..."/>
        </div>
      );
  } else if (flags.length === 0) {
      return (
        <div>
          <h2>Describe the flag using words</h2>
          <SubmitDescriptionForm addFlag={addFlag} />
          <h2>Or upload a picture</h2>
          <ImageUploader addImageUpload={addImageUpload} />
          <button
          onClick={handleClick}
          style={{ backgroundColor: '#FFCECE', color: 'black' }}
          >
            Clear
          </button>
          <ImageGrid images={image_flags} title="I bet it's..."/>
        </div>
      );
  }
};

export default FlagList;
