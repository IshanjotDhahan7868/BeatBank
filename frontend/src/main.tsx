// src/main.tsx

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import "./index.css";

import { AuthProvider } from "./context/AuthContext";

import App from "./App";
import Home from "./pages/Home";
import Generate from "./pages/Generate";
import History from "./pages/History";
import Detail from "./pages/Detail";
import Login from "./pages/Login";
import Signup from "./pages/Signup";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<App />}>
            <Route path="/" element={<Home />} />

            {/* Auth */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* User-only pages */}
            <Route path="/generate" element={<Generate />} />
            <Route path="/history" element={<History />} />
            <Route path="/detail/:id" element={<Detail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
