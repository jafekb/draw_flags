import axios from 'axios';

// Create an instance of axios with the base URL
const api = axios.create({
  baseURL: import.meta.env.DEV
    ? "http://localhost:8000"
    : (import.meta.env.VITE_API_URL || "https://draw-flags.onrender.com")
});

// Text search function
export const searchByText = async (textQuery) => {
  const response = await api.post('/search/text', { text_query: textQuery });
  return response;
};

// Image search function
export const searchByImage = async (imageFile) => {
  const formData = new FormData();
  formData.append('file', imageFile);
  
  const response = await api.post('/search/image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response;
};

// Export the Axios instance
export default api;
