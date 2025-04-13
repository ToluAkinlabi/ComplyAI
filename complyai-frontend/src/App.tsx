// src/App.tsx

import { useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import MobileSidebarToggle from "./components/MobileSidebarToggle";
import Header from "./components/Header";
import UploadPage from "./pages/UploadPage";
import ReportPage from "./pages/ReportPage";
import DashboardPage from "./dashboard/DashboardPage";

const App = () => {
    const [isSidebarOpen, setSidebarOpen] = useState(false);

    return (
        <div className="flex min-h-screen overflow-hidden bg-gray-100 dark:bg-gray-800">
        <Sidebar isOpen={isSidebarOpen} onClose={() => setSidebarOpen(false)} />
        
        <div className="flex-1 flex flex-col h-screen overflow-y-auto">
            <Header setSidebarOpen={setSidebarOpen} />
            <main className="flex-1 p-6 overflow-y-auto">
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

    );
};

export default App;

