import { HashRouter, Routes, Route, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

import Splash from "../pages/Splash";
import Login from "../pages/Login";
import Signup from "../pages/Signup";
import Dashboard from "../pages/Dashboard";
import Exams from "../pages/Exams";
import ExamDetails from "../pages/ExamDetails";
import ResultsPage from "../pages/ResultsPage";

import AdminLayout from "../layout/AdminLayout";
import ProtectedRoute from "./ProtectedRoute";

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        
        {/* ================= PUBLIC ROUTES ================= */}
        <Route path="/" element={<Splash />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* ================= PROTECTED ROUTES ================= */}
        <Route
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          {/* Dashboard */}
          <Route path="/dashboard" element={<Dashboard />} />

          {/* Exams */}
          <Route path="/exams" element={<Exams />} />
          <Route path="/exams/:examId" element={<ExamDetails />} />

          {/* 🔥 Unified Results Page */}
          <Route path="/results" element={<ResultsPage />} />
        </Route>

      </Routes>
    </AnimatePresence>
  );
}

export default function AppRouter() {
  return (
    <HashRouter>
      <AnimatedRoutes />
    </HashRouter>
  );
}