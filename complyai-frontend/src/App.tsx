// src/App.tsx

import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import UploadPage from "./pages/UploadPage";
import ReportPage from "./pages/ReportPage";
import DashboardPage from "./dashboard/DashboardPage";

function App() {
    return (
        <Router>
            <div className="flex h-screen">
                <Sidebar />
                <div className="flex-1 flex flex-col">
                    <Header />
                    <main className="p-6 bg-gray-50 flex-1 overflow-y-auto">
                      <Routes>
                        <Route path="/" element={<Navigate to="/dashboard/upload" replace />} />
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/dashboard/upload" element={<UploadPage />} />
                        <Route path="/dashboard/report" element={<ReportPage />} />
                      </Routes>
                    </main>
                </div>
                <Toaster position="top-right" />
            </div>
        </Router>
    );
}

export default App;
