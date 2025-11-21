import { useEffect, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";

interface Beat {
  id: number;
  title: string;
  description: string;
  image_path: string | null;
  created_at?: string;
}

export default function History() {
  const [beats, setBeats] = useState<Beat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.history();
        setBeats(res.data || []);
      } catch (err) {
        console.error("History error:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  if (loading) return <div className="p-12 text-center text-gray-500">Loading...</div>;
  if (!beats.length)
    return <div className="p-12 text-center text-gray-500">No beats generated yet.</div>;

  return (
    <div className="p-10 text-white">
      <h1 className="text-3xl font-bold mb-6">Your Library</h1>

      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {beats.map((beat) => (
          <Link
            key={beat.id}
            to={`/detail/${beat.id}`}
            className="bg-gray-800 rounded-lg overflow-hidden hover:ring-2 hover:ring-purple-400 transition"
          >
            {beat.image_path ? (
              <img
                src={`${import.meta.env.VITE_API_BASE_URL}/artifacts/${beat.image_path}`}
                className="w-full h-48 object-cover"
              />
            ) : (
              <div className="w-full h-48 flex items-center justify-center text-gray-500 bg-gray-700">
                No Image
              </div>
            )}

            <div className="p-4">
              <p className="text-lg font-semibold">{beat.title}</p>
              <p className="text-xs text-gray-400">{beat.created_at?.slice(0, 10)}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
