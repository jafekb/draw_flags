import axios from 'axios';

// Create an instance of axios with the base URL
const api = axios.create({
  baseURL: import.meta.env.DEV
    ? "http://localhost:8000"
    : (import.meta.env.VITE_API_URL || "https://draw-flags.onrender.com")
});

// Export the Axios instance
export default api;
