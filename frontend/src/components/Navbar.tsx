// src/components/Navbar.tsx

import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="w-full bg-gray-900 text-white flex items-center gap-6 px-6 py-4 border-b border-gray-800">
      <Link to="/" className="font-bold text-lg">BeatBank</Link>

      <div className="flex gap-4 text-sm">
        <Link to="/generate">Generate</Link>
        <Link to="/history">History</Link>
      </div>
    </nav>
  );
}
