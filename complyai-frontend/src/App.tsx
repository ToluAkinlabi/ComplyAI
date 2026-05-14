// src/App.tsx

import { ReactNode, useState } from "react";
import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import UploadPage from "./pages/UploadPage";
import ReportPage from "./pages/ReportPage";
import DashboardPage from "./dashboard/DashboardPage";
import LoginPage from "./pages/LoginPage";
import { api } from "./api";
import { clearAllAuth, getRefreshToken, getUserDisplayName, isAuthenticated } from "./auth";
import InviteManagePage from "./dashboard/InviteManagePage";
import AcceptInvitePage from "./pages/AcceptInvitePage";

interface ShellProps {
    isSidebarOpen: boolean;
    setSidebarOpen: (open: boolean) => void;
    onLogout: () => void;
    children: ReactNode;
}

const DashboardShell = ({ isSidebarOpen, setSidebarOpen, onLogout, children }: ShellProps) => {
    const userName = getUserDisplayName();

    return (
        <div className="flex min-h-screen overflow-hidden bg-gray-100 dark:bg-gray-800">
            <Sidebar isOpen={isSidebarOpen} onClose={() => setSidebarOpen(false)} />

            <div className="flex-1 flex flex-col h-screen overflow-y-auto">
                <Header setSidebarOpen={setSidebarOpen} userName={userName} onLogout={onLogout} />
                <main className="flex-1 p-6 overflow-y-auto">{children}</main>
            </div>
        </div>
    );
};

const RequireAuth = ({ children }: { children: ReactNode }) => {
    const location = useLocation();
    if (!isAuthenticated()) {
        const next = encodeURIComponent(`${location.pathname}${location.search}`);
        return <Navigate to={`/login?next=${next}`} replace />;
    }
    return <>{children}</>;
};

const App = () => {
        const [isSidebarOpen, setSidebarOpen] = useState(false);
        const navigate = useNavigate();

        const handleLogout = async () => {
            const refreshToken = getRefreshToken();
            try {
                if (refreshToken) {
                    await api.post("/auth/logout", { refresh_token: refreshToken });
                }
            } catch {
                // Ignore logout API failures and proceed with local session teardown.
            } finally {
                clearAllAuth();
                setSidebarOpen(false);
                navigate("/login", { replace: true });
            }
        };

    return (
            <>
                <Toaster position="top-right" />
                <Routes>
                    <Route path="/" element={<Navigate to={isAuthenticated() ? "/dashboard/upload" : "/login"} replace />} />
                    <Route path="/login" element={isAuthenticated() ? <Navigate to="/dashboard/upload" replace /> : <LoginPage />} />

                    <Route
                        path="/dashboard"
                        element={
                            <RequireAuth>
                                <DashboardShell isSidebarOpen={isSidebarOpen} setSidebarOpen={setSidebarOpen} onLogout={handleLogout}>
                                    <DashboardPage />
                                </DashboardShell>
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/dashboard/upload"
                        element={
                            <RequireAuth>
                                <DashboardShell isSidebarOpen={isSidebarOpen} setSidebarOpen={setSidebarOpen} onLogout={handleLogout}>
                                    <UploadPage />
                                </DashboardShell>
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/dashboard/report"
                        element={
                            <RequireAuth>
                                <DashboardShell isSidebarOpen={isSidebarOpen} setSidebarOpen={setSidebarOpen} onLogout={handleLogout}>
                                    <ReportPage />
                                </DashboardShell>
                            </RequireAuth>
                        }
                    />

                    <Route
                        path="/dashboard/invites"
                        element={
                            <RequireAuth>
                                <DashboardShell isSidebarOpen={isSidebarOpen} setSidebarOpen={setSidebarOpen} onLogout={handleLogout}>
                                    <InviteManagePage />
                                </DashboardShell>
                            </RequireAuth>
                        }
                    />

                    <Route path="/invite/:token" element={<AcceptInvitePage />} />

                    <Route path="*" element={<Navigate to={isAuthenticated() ? "/dashboard/upload" : "/login"} replace />} />
                </Routes>
            </>

    );
};

export default App;

