// src/pages/History.tsx
import { useEffect, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";

interface Beat {
  id: string;
  title: string;
  description: string;
  image_path: string | null;
  video_path: string | null;
  ai_video_path: string | null;
  created_at?: string;
  tags?: string[];
}

export default function History() {
  const [beats, setBeats] = useState<Beat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await api.history();
        setBeats(res.data || []);
      } catch (err) {
        console.error("Error loading history:", err);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, []);

  if (loading)
    return <div className="p-8 text-center text-gray-400">Loading your beats...</div>;

  if (!beats.length)
    return <div className="p-8 text-center text-gray-400">No beats generated yet.</div>;

  return (
    <div className="min-h-screen p-8 text-white bg-gradient-to-b from-gray-900 to-black">
      <h1 className="text-3xl font-bold mb-6">Your Generated Beats</h1>

      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {beats.map((beat) => (
          <Link
            key={beat.id}
            to={`/detail/${beat.id}`}
            className="bg-gray-800 rounded-xl overflow-hidden hover:ring-2 hover:ring-purple-500 transition"
          >
            {beat.image_path ? (
              <img
                src={
                  beat.image_path.startsWith("http")
                    ? beat.image_path
                    : `${import.meta.env.VITE_API_BASE_URL}/artifacts/${beat.image_path}`
                }
                alt={beat.title}
                className="w-full h-48 object-cover"
              />
            ) : (
              <div className="h-48 flex items-center justify-center bg-gray-700 text-gray-500">
                No image
              </div>
            )}
            <div className="p-4">
              <h2 className="text-lg font-semibold">{beat.title}</h2>
              <p className="text-gray-400 text-sm line-clamp-2">
                {beat.description}
              </p>
              {beat.tags && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {beat.tags.map((tag, i) => (
                    <span
                      key={i}
                      className="text-xs bg-purple-700/40 px-2 py-1 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
