import axios from "axios";

// Create an instance of axios with the base URL
const baseURL = import.meta.env.VITE_API_URL || 
    (import.meta.env.DEV
      ? "http://localhost:8000"
      : "https://draw-flags.onrender.com");

console.log("API Base URL:", baseURL);
console.log("VITE_API_URL:", import.meta.env.VITE_API_URL);
console.log("DEV mode:", import.meta.env.DEV);

const api = axios.create({
  baseURL: baseURL,
});

// Export the Axios instance
export default api;
