import React, { useState } from 'react';

const SubmitDescriptionForm = ({ addFlag }) => {
  const [flagName, setFlagName] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    if (flagName) {
      addFlag(flagName);
      setFlagName('');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={flagName}
        onChange={(e) => setFlagName(e.target.value)}
        placeholder="Describe it"
      />
      <button type="submit">Submit</button>
    </form>
  );
};

export default SubmitDescriptionForm;
