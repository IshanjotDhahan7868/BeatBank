// src/App.tsx

import { Outlet } from "react-router-dom";
import { Toaster } from "sonner";
import Navbar from "./components/Navbar";

export default function App() {
  return (
    <>
      <Navbar />
      <Toaster richColors position="top-right" />
      <main className="min-h-screen bg-gray-950 text-white p-6">
        <Outlet />
      </main>
    </>
  );
}
