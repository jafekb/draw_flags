import React, { useState } from "react";

const SubmitDescriptionForm = ({ addFlag }) => {
  const [flagName, setFlagName] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    if (flagName) {
      addFlag(flagName);
      setFlagName("");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="description-form">
      <input
        className="description-input"
        type="text"
        value={flagName}
        onChange={(e) => setFlagName(e.target.value)}
        placeholder="Describe the flag in words"
      />
      <button className="description-submit" type="submit">
        Submit
      </button>
    </form>
  );
};

export default SubmitDescriptionForm;
