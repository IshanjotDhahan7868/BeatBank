// ✅ FULLY FIXED, CLEAN, WORKING Generate.tsx
// ✅ UI preserved
// ✅ Correct imports
// ✅ Correct API_BASE_URL usage
// ✅ No TypeScript or JSX errors

import { useState, useRef } from "react";
import api, { API_BASE_URL } from "../lib/api";


export default function Generate() {
  const [prompt, setPrompt] = useState("");

  const [doMetadata, setDoMetadata] = useState(true);
  const [doImage, setDoImage] = useState(true);
  const [doMusic, setDoMusic] = useState(true);
  const [doVisualizer, setDoVisualizer] = useState(true);
  const [doAIVideo, setDoAIVideo] = useState(false);

  const [waveform, setWaveform] = useState(true);
  const [spectrum, setSpectrum] = useState(false);
  const [pulse, setPulse] = useState(true);
  const [zoom, setZoom] = useState(true);
  const [vhs, setVhs] = useState(false);

  const [provider, setProvider] = useState("auto");
  const [aiVideoProvider, setAiVideoProvider] = useState("runway");
  const [duration, setDuration] = useState(30);
  const [audioFormat, setAudioFormat] = useState("mp3");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

  const abortRef = useRef<AbortController | null>(null);

  const log = (msg: string) => setLogs((p) => [...p, msg]);

  async function generate() {
    setLoading(true);
    setError("");
    setLogs([]);
    setResult(null);
    log("Starting generation…");

    const form = new FormData();
    form.append("prompt", prompt);
    form.append("do_metadata", String(doMetadata));
    form.append("do_image", String(doImage));
    form.append("do_music", String(doMusic));
    form.append("do_visualizer", String(doVisualizer));
    form.append("do_ai_video", String(doAIVideo));
    form.append("provider", provider);
    form.append("ai_video_provider", aiVideoProvider);
    form.append("duration", String(duration));
    form.append("audio_format", audioFormat);

    form.append("waveform", String(waveform));
    form.append("spectrum", String(spectrum));
    form.append("pulse", String(pulse));
    form.append("zoom", String(zoom));
    form.append("vhs", String(vhs));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      log("Sending to backend…");
      const { data } = await api.post("/api/auto", form, { signal: controller.signal });
      log("✅ Generation complete");
      setResult(data);
    } catch (err: any) {
      if (err.name === "AbortError") log("❌ Cancelled");
      else {
        setError("Generation failed.");
        log("❌ Error occurred");
      }
    }

    setLoading(false);
  }

  function cancel() {
    if (abortRef.current) abortRef.current.abort();
    setLoading(false);
    log("⚠️ User cancelled generation.");
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white flex">
      <aside className="w-60 bg-gray-900 p-6 space-y-4 border-r border-gray-800">
        <h1 className="text-xl font-bold">BeatBank</h1>
        <nav className="space-y-2">
          <div className="text-purple-400 font-semibold">Generate</div>
          <div className="text-gray-500">History</div>
          <div className="text-gray-500">Account</div>
        </nav>
      </aside>

      <main className="flex-1 p-8 overflow-y-auto space-y-8">
        <h2 className="text-3xl font-bold">Generate Beat</h2>

        <div className="grid grid-cols-2 gap-6">
          {/* LEFT SIDE */}
          <div className="space-y-6">
            {/* ✅ Prompt */}
            <div className="bg-gray-900 p-4 rounded-xl space-y-3">
              <h3 className="font-bold">Prompt</h3>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full bg-gray-800 p-3 rounded h-32"
                placeholder="Describe your beat idea…"
              />
            </div>

            {/* ✅ Steps */}
            <div className="bg-gray-900 p-4 rounded-xl space-y-2">
              <h3 className="font-bold">Steps</h3>
              <label><input type="checkbox" checked={doMetadata} onChange={e=>setDoMetadata(e.target.checked)} /> Metadata</label><br/>
              <label><input type="checkbox" checked={doImage} onChange={e=>setDoImage(e.target.checked)} /> Image</label><br/>
              <label><input type="checkbox" checked={doMusic} onChange={e=>setDoMusic(e.target.checked)} /> Music</label><br/>
              <label><input type="checkbox" checked={doVisualizer} onChange={e=>setDoVisualizer(e.target.checked)} /> Visualizer</label><br/>
              <label><input type="checkbox" checked={doAIVideo} onChange={e=>setDoAIVideo(e.target.checked)} /> AI Video</label>
            </div>

            {/* ✅ Providers + Duration */}
            <div className="bg-gray-900 p-4 rounded-xl space-y-4">
              <div>
                <h3 className="font-bold">Music Provider</h3>
                <select className="bg-gray-800 p-2 rounded w-full" value={provider} onChange={e=>setProvider(e.target.value)}>
                  <option value="auto">Auto</option>
                  <option value="replicate">Replicate</option>
                  <option value="local">Local</option>
                </select>
              </div>

              {doAIVideo && (
                <div>
                  <h3 className="font-bold">AI Video Provider</h3>
                  <select className="bg-gray-800 p-2 rounded w-full" value={aiVideoProvider} onChange={e=>setAiVideoProvider(e.target.value)}>
                    <option value="runway">Runway Gen-3</option>
                    <option value="pika">Pika</option>
                  </select>
                </div>
              )}

              <div>
                <h3 className="font-bold">Duration: {duration}s</h3>
                <input type="range" min={5} max={60} value={duration} onChange={e=>setDuration(Number(e.target.value))} className="w-full"/>
              </div>

              <div>
                <h3 className="font-bold">Audio Format</h3>
                <select className="bg-gray-800 p-2 rounded w-full" value={audioFormat} onChange={e=>setAudioFormat(e.target.value)}>
                  <option value="mp3">MP3</option>
                  <option value="wav">WAV</option>
                  <option value="both">Both</option>
                </select>
              </div>
            </div>

            {/* ✅ Visualizer FX */}
            <div className="bg-gray-900 p-4 rounded-xl space-y-2">
              <h3 className="font-bold">Visualizer FX</h3>
              <label><input type="checkbox" checked={waveform} onChange={e=>setWaveform(e.target.checked)} /> Waveform</label><br/>
              <label><input type="checkbox" checked={spectrum} onChange={e=>setSpectrum(e.target.checked)} /> Spectrum</label><br/>
              <label><input type="checkbox" checked={pulse} onChange={e=>setPulse(e.target.checked)} /> Pulse</label><br/>
              <label><input type="checkbox" checked={zoom} onChange={e=>setZoom(e.target.checked)} /> Zoom</label><br/>
              <label><input type="checkbox" checked={vhs} onChange={e=>setVhs(e.target.checked)} /> VHS</label>
            </div>

            {/* ✅ Buttons */}
            <button className="bg-purple-600 px-4 py-2 rounded w-full" onClick={generate} disabled={loading}>
              {loading ? "Generating…" : "Generate"}
            </button>
            {loading && (
              <button className="bg-red-600 px-4 py-2 rounded w-full" onClick={cancel}>Cancel</button>
            )}

            {error && <div className="text-red-400">{error}</div>}
          </div>

          {/* ✅ RIGHT SIDE */}
          <div className="space-y-6">
            {/* ✅ Logs */}
            <div className="bg-gray-900 p-4 rounded-xl h-40 overflow-y-auto text-sm space-y-1">
              <h3 className="font-bold mb-1">Logs</h3>
              {logs.map((l, i) => <div key={i}>{l}</div>)}
            </div>

            {/* ✅ Results */}
            {result && (
              <div className="space-y-6">

                {/* Metadata */}
                {result.metadata && (
                  <div className="bg-gray-900 p-4 rounded-xl">
                    <h3 className="font-bold text-lg">Metadata</h3>
                    <p>Title: {result.metadata.title}</p>
                    <p>Tags: {result.metadata.tags.join(", ")}</p>
                    <p className="opacity-80">{result.metadata.description}</p>
                  </div>
                )}

                {/* DSP */}
                {result.dsp && (
                  <div className="bg-gray-900 p-4 rounded-xl">
                    <h3 className="font-bold text-lg mb-2">DSP Stats</h3>
                    {Object.entries(result.dsp).map(([k, v]) => (
                      <p key={k}>{k}: {String(v)}</p>
                    ))}
                  </div>
                )}

                {/* Image */}
                {result.image_path && (
                  <img
                    className="rounded-xl"
                    src={`${API_BASE_URL}/${result.image_path}`}
                  />
                )}

                {/* Audio */}
                {result.audio_paths && (
                  <audio
                    controls
                    src={`${API_BASE_URL}/${result.audio_paths[0]}`}
                    className="w-full"
                  />
                )}

                {/* Video */}
                {result.video_path && (
                  <video
                    controls
                    src={`${API_BASE_URL}/${result.video_path}`}
                    className="rounded-xl w-full"
                  />
                )}

                {/* AI Video */}
                {result.ai_video_path && (
                  <video
                    controls
                    src={`${API_BASE_URL}/${result.ai_video_path}`}
                    className="rounded-xl w-full"
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
