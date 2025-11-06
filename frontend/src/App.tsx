import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Generate from "./pages/Generate";
import History from "./pages/History";
import Detail from "./pages/Detail";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/generate" element={<Generate />} />
        <Route path="/history" element={<History />} />
        <Route path="/beat/:id" element={<Detail />} />
      </Routes>
    </BrowserRouter>
  );
}

