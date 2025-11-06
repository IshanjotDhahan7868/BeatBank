// src/pages/Home.tsx
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      {/* BG grid patterns */}
      <div className="absolute inset-0 bg-grid-white/[0.03] bg-[size:32px_32px]" />

      {/* Centered Hero */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center min-h-screen px-6">
        <motion.h1
          className="text-5xl md:text-6xl font-bold drop-shadow-xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          BeatBank Elite Creator Mode
        </motion.h1>

        <motion.p
          className="mt-4 text-lg md:text-xl opacity-70 max-w-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          Generate music, artwork, metadata, and videos — instantly.
        </motion.p>

        {/* BUTTONS */}
        <motion.div
          className="mt-8 flex space-x-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <Link to="/generate">
            <button className="rounded-full px-8 py-3 bg-white text-black text-sm font-medium shadow hover:shadow-lg">
              Start Creating →
            </button>
          </Link>

          <Link to="/history">
            <button className="rounded-full px-8 py-3 bg-white/10 border border-white/20 text-sm hover:bg-white/15">
              Explore Library
            </button>
          </Link>
        </motion.div>
      </div>

      {/* Decorative glow */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-500/5 to-transparent pointer-events-none" />
    </div>
  );
}

