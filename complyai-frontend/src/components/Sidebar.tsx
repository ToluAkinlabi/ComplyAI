// src/components/Sidebar.tsx

import { NavLink } from "react-router-dom";
import { FaFileUpload, FaFileAlt, FaTachometerAlt } from "react-icons/fa";
import ThemeToggle from "./ThemeToggle";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const Sidebar = ({ isOpen, onClose }: SidebarProps) => {
  const navLinks = (
    <nav className="flex flex-col space-y-2 p-2 pt-10 md:pt-4 text-sm sm:text-base">
        <div className="md:hidden flex justify-end pt-2">
            <button
                onClick={onClose}
                className="text-white text-xl hover:text-gray-300 focus:outline-none"
            >
                &times;
            </button>
        </div>
        <NavLink
            to="/dashboard/upload"
            className={({ isActive }) => `flex items-center space-x-2 px-3 py-2 rounded-md hover:bg-gray-700 transition ${isActive ? "bg-gray-700" : ""}`}
        >
            <FaFileUpload />
            <span>Upload</span>
        </NavLink>

        <NavLink
            to="/dashboard/report"
            className={({ isActive }) => `flex items-center space-x-2 px-3 py-2 rounded-md hover:bg-gray-700 transition ${isActive ? "bg-gray-700" : ""}`}
        >
            <FaFileAlt />
            <span>Reports</span>
        </NavLink>

        <NavLink
            to="/dashboard"
            end
            className={({ isActive }) => `flex items-center space-x-2 px-3 py-2 rounded-md hover:bg-gray-700 transition ${isActive ? "bg-gray-700" : ""}`}
        >
            <FaTachometerAlt />
            <span>Dashboard</span>
        </NavLink>
    </nav>
  );

  const footer = (
    <div className="flex justify-between items-center text-[8px] sm:text-xs text-gray-400 py-3 sm:py-4 border-t border-gray-700 px-4">
      <ThemeToggle />
      <p className="text-xs">&copy; {new Date().getFullYear()} ComplyAI Inc.</p>
    </div>
  );

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-40 md:hidden"
          onClick={onClose}
        />
      )}
  
      {/* Desktop Sidebar */}
      <aside className="w-64 min-h-screen md:h-auto md:sticky top-0 bg-gradient-to-b from-gray-900 to-gray-800 text-white flex flex-col justify-between shadow-lg hidden md:flex">
        <div>{navLinks}</div>
        {footer}
      </aside>
  
      {/* Mobile Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 bg-gradient-to-b from-gray-900 to-gray-800 text-white w-64 p-4 flex flex-col justify-between shadow-lg transform transition-transform duration-300 ease-in-out md:hidden ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div>{navLinks}</div>
        {footer}
      </aside>
    </>
  );
};

export default Sidebar;
