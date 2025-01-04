import React, { useEffect, useState } from 'react';
import api from "../api.js";
import SubmitDescriptionForm from './SubmitDescriptionForm';

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

  return (
    <div>
      <h2>Describe the flag using words or a picture</h2>
      <ul>
        {flags.map((flag, index) => (
          <li key={index}>yo: {flag.name}</li>
        ))}
      </ul>
      <SubmitDescriptionForm addFlag={addFlag} />
    </div>
  );
};

export default FlagList;
