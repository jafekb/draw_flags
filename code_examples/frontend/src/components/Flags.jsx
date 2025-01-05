import React, { useEffect, useState } from 'react';
import api from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from './SubmitDescriptionForm';
import ImageUploader from './ImageUploader';

const FlagList = () => {
  const [flags, setFlags] = useState([]);

  const fetchFlags = async () => {
    try {
      const response = await api.get('/flags');
      setFlags(response.data.flags);
    } catch (error) {
      console.error("Error fetching flags", error);
    }
  };

  const addFlag = async (flagName) => {
    try {
      await api.post('/flags', { name: flagName });
      fetchFlags();  // Refresh the list after adding a flag
    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, []);

  if (flags.length === 0) {
      return (
        <div>
          <h2>Describe the flag using words or a picture</h2>
          <SubmitDescriptionForm addFlag={addFlag} />
        </div>
      );
  }

  // TODO(bjafek) do this if-statement less clumsily
  return (
    <div>
      <h2>Describe the flag using words or a picture</h2>
      <SubmitDescriptionForm addFlag={addFlag} />
      <ImageGrid images={flags} title="I bet it's..."/>
    </div>
  );
};

export default FlagList;
