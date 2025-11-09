// src/lib/api.ts
import axios from "axios";

// ✅ Environment variable from Vercel (.env)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// ✅ Safety check
if (!API_BASE_URL) {
  console.warn("⚠️ VITE_API_BASE_URL is missing! Add it in Vercel → Environment Variables.");
}

// ✅ Axios instance (this is what GenerateDashboardFinal expects)
const api = axios.create({
  baseURL: API_BASE_URL,
});

// ✅ Default export (your component imports: `import api from "../lib/api"`)
export default api;

// ✅ Named export for building full URLs (for displaying image/audio/video)
export { API_BASE_URL };
