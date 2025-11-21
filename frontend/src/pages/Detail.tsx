import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../lib/api";

export default function Detail() {
  const { id } = useParams();
  const [beat, setBeat] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.detail(id!);
        setBeat(res.data);
      } catch (err) {
        console.error("Detail error:", err);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [id]);

  if (loading) return <div className="p-12 text-center text-gray-400">Loading...</div>;
  if (!beat) return <div className="p-12 text-center text-gray-400">Not found.</div>;

  return (
    <div className="p-10 text-white max-w-4xl mx-auto">

      <h1 className="text-3xl font-bold mb-4">{beat.title}</h1>
      <p className="text-gray-400 mb-6">{beat.description}</p>

      {beat.image_path && (
        <img
          src={`${import.meta.env.VITE_API_BASE_URL}/artifacts/${beat.image_path}`}
          className="rounded-xl w-full mb-6 shadow-lg"
        />
      )}

      {beat.video_path && (
        <video controls className="w-full rounded-xl shadow-lg mb-6">
          <source
            src={`${import.meta.env.VITE_API_BASE_URL}/artifacts/${beat.video_path}`}
            type="video/mp4"
          />
        </video>
      )}

      {beat.ai_video_path && (
        <video controls className="w-full rounded-xl shadow-lg mb-6">
          <source
            src={`${import.meta.env.VITE_API_BASE_URL}/artifacts/${beat.ai_video_path}`}
            type="video/mp4"
          />
        </video>
      )}

      {beat.file_name && (
        <audio controls className="w-full mt-4">
          <source
            src={`${import.meta.env.VITE_API_BASE_URL}/artifacts/${beat.file_name}`}
            type="audio/mp3"
          />
        </audio>
      )}

    </div>
  );
}
