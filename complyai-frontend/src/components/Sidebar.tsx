// src/components/Sidebar.tsx
import { Link, useLocation } from "react-router-dom";

const Sidebar = () => {
  const location = useLocation();

  const isActive = (path: string) =>
    location.pathname === path ? "bg-blue-700" : "hover:bg-blue-600";

  return (
    <div className="w-64 h-screen bg-gray-800 text-white flex flex-col p-4 space-y-6">
      <h1 className="text-2xl font-bold mb-4">Comply</h1>

      <nav className="flex flex-col space-y-2">
        <Link
          to="/dashboard/upload"
          className={`p-2 rounded ${isActive("/dashboard/upload")}`}
        >
          Upload Policy
        </Link>
        <Link
          to="/dashboard/report"
          className={`p-2 rounded ${isActive("/dashboard/report")}`}
        >
          View Reports
        </Link>
      </nav>
    </div>
  );
};

export default Sidebar;