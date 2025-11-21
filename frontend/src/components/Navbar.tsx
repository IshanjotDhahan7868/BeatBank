// src/components/Navbar.tsx

import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { supabase } from "../lib/supabase";
import { toast } from "sonner";

export default function Navbar() {
  const { user } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await supabase.auth.signOut();
    toast.success("Logged out");
    navigate("/login");
  }

  return (
    <nav className="w-full bg-gray-900 text-white flex justify-between items-center px-6 py-4 border-b border-gray-800">
      <Link to="/" className="font-bold text-lg">
        BeatBank
      </Link>

      <div className="flex gap-4 text-sm items-center">
        {user && (
          <>
            <Link to="/generate">Generate</Link>
            <Link to="/history">History</Link>
          </>
        )}

        {!user ? (
          <>
            <Link to="/login" className="hover:text-purple-400">Login</Link>
            <Link to="/signup" className="hover:text-purple-400">Sign Up</Link>
          </>
        ) : (
          <button
            onClick={handleLogout}
            className="text-red-400 hover:text-red-300"
          >
            Logout
          </button>
        )}
      </div>
    </nav>
  );
}
