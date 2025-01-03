import React, { useState } from 'react';

const SubmitDescriptionForm = ({ addFruit }) => {
  const [fruitName, setFruitName] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    if (fruitName) {
      addFruit(fruitName);
      setFruitName('');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={fruitName}
        onChange={(e) => setFruitName(e.target.value)}
        placeholder="Describe it"
      />
      <button type="submit">Submit</button>
    </form>
  );
};

export default SubmitDescriptionForm;
