// src/lib/api.ts

// ✅ Load API base URL from environment variable (.env)
export const API_URL = import.meta.env.VITE_API_URL;

// ✅ Helper: always ensure API_URL exists
if (!API_URL) {
  console.warn(
    "⚠️ VITE_API_URL is missing! Add it to your frontend/.env file."
  );
}

// --------------------------------------------------------------
// ✅ Upload Beat (POST /api/upload)
// --------------------------------------------------------------

export async function uploadBeat(formData: FormData) {
  const response = await fetch(`${API_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Upload failed");
  }

  return response.json();
}

// --------------------------------------------------------------
// ✅ Generate Metadata (POST /api/metadata)
// --------------------------------------------------------------

export async function generateMetadata(data: any) {
  const response = await fetch(`${API_URL}/api/metadata`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Metadata generation failed");
  }

  return response.json();
}

// --------------------------------------------------------------
// ✅ Generate Visualizer (POST /api/visualizer)
// --------------------------------------------------------------

export async function generateVisualizer(data: any) {
  const response = await fetch(`${API_URL}/api/visualizer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Visualizer generation failed");
  }

  return response.json();
}

// --------------------------------------------------------------
// ✅ Get History (GET /api/history)
// --------------------------------------------------------------

export async function getHistory() {
  const response = await fetch(`${API_URL}/api/history`);

  if (!response.ok) {
    throw new Error("Failed to load history");
  }

  return response.json();
}

// --------------------------------------------------------------
// ✅ Get Details (GET /api/detail/:id)
// --------------------------------------------------------------

export async function getDetail(id: string) {
  const response = await fetch(`${API_URL}/api/detail/${id}`);

  if (!response.ok) {
    throw new Error("Failed to fetch detail");
  }

  return response.json();
}
