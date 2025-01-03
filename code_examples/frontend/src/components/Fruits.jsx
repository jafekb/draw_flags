import React, { useEffect, useState } from 'react';
import api from "../api.js";
import SubmitDescriptionForm from './SubmitDescriptionForm';

const FruitList = () => {
  const [fruits, setFruits] = useState([]);

  const fetchFruits = async () => {
    try {
      const response = await api.get('/fruits');
      setFruits(response.data.fruits);
    } catch (error) {
      console.error("Error fetching fruits", error);
    }
  };

  const addFruit = async (fruitName) => {
    try {
      await api.post('/fruits', { name: fruitName });
      fetchFruits();  // Refresh the list after adding a fruit
    } catch (error) {
      console.error("Error adding fruit", error);
    }
  };

  useEffect(() => {
    fetchFruits();
  }, []);

  return (
    <div>
      <h2>Describe the flag using words or a picture</h2>
      <ul>
        {fruits.map((fruit, index) => (
          <li key={index}>yo: {fruit.name}</li>
        ))}
      </ul>
      <SubmitDescriptionForm addFruit={addFruit} />
    </div>
  );
};

export default FruitList;
