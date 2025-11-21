// src/lib/api.ts

// ✅ Load backend URLs from frontend/.env
export const API_URL = import.meta.env.VITE_API_URL;
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// ✅ Warn if environment variables missing
if (!API_URL) console.warn("⚠️ Missing VITE_API_URL in frontend/.env");
if (!API_BASE_URL) console.warn("⚠️ Missing VITE_API_BASE_URL in frontend/.env");

// --------------------------------------------------------------
// ✅ INTERNAL REQUEST WRAPPER
// --------------------------------------------------------------

async function request(
  method: string,
  url: string,
  body?: any,
  isForm: boolean = false,
  extraOptions: any = {}
) {
  const options: RequestInit = {
    method,
    ...extraOptions,
  };

  if (body) {
    if (isForm) {
      options.body = body;
    } else {
      options.body = JSON.stringify(body);
      options.headers = { "Content-Type": "application/json" };
    }
  }

  const res = await fetch(`${API_URL}${url}`, options);

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed (${res.status}): ${text}`);
  }

  return res.json();
}

// --------------------------------------------------------------
// ✅ PUBLIC API (Used by your Generate & History pages)
// --------------------------------------------------------------

const api = {
  // Generic POST used by some calls in your Generate page
  post: (url: string, data: any, options?: any) =>
    request("POST", url, data, false, options),

  // Upload & full auto-processing: POST /api/auto
  auto: (form: FormData) =>
    request("POST", "/api/auto", form, true),

  // Metadata generation: POST /api/metadata
  metadata: (data: any) =>
    request("POST", "/api/metadata", data),

  // Visualizer generation: POST /api/visualizer
  visualizer: (data: any) =>
    request("POST", "/api/visualizer", data),

  // History list: GET /api/history
  history: () =>
    request("GET", "/api/history"),

  // Detail for single entry: GET /api/detail/:id
  detail: (id: string) =>
    request("GET", `/api/detail/${id}`),
};

export default api;
