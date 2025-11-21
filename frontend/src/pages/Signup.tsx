import { useState } from "react";
import { supabase } from "../lib/supabase";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault();

    const { error } = await supabase.auth.signUp({
      email,
      password,
    });

    if (error) return toast.error(error.message);

    toast.success("Check your email to confirm your account!");
    navigate("/login");
  }

  return (
    <div className="p-10 max-w-md mx-auto text-white">
      <h1 className="text-3xl font-bold mb-6">Create Account</h1>

      <form onSubmit={handleSignup} className="space-y-4">
        <input
          type="email"
          placeholder="Email"
          className="w-full p-3 rounded bg-gray-800"
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          className="w-full p-3 rounded bg-gray-800"
          onChange={(e) => setPassword(e.target.value)}
        />

        <button className="w-full bg-purple-600 p-3 rounded font-semibold">
          Sign Up
        </button>
      </form>
    </div>
  );
}
