import React, { useEffect, useState } from "react";
import api from "../api.js";
import ImageGrid from "./ImageGrid";
import SubmitDescriptionForm from "./SubmitDescriptionForm";

const FlagList = () => {
  const [flags, setFlags] = useState([]);

  const addFlag = async (textQuery) => {
    try {
      const response = await api.post("/", { text_query: textQuery });
      setFlags(response.data.flags)

    } catch (error) {
      console.error("Error adding flag", error);
    }
  };

  return (
    <div>
      <h2>Describe the flag using words</h2>
      <SubmitDescriptionForm addFlag={addFlag} />

      {flags.length === 0 ? null : (
        <>
          <button
            onClick={() => setFlags([])}
            style={{ backgroundColor: "#FFCECE", color: "black" }}
          >
            Clear
          </button>
          <ImageGrid images={flags} title="I bet it's..." />
        </>
      )}
    </div>
  );
};

export default FlagList;
