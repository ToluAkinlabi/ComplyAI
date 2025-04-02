// Sidebar.tsx

import { NavLink } from "react-router-dom";
import { FaFileUpload, FaFileAlt } from "react-icons/fa";

const Sidebar = () => {
    return (
        <aside className="w-64 h-screen bg-gradient-to-b from-gray-900 to-gray-800 text-white flex flex-col justify-between shadow-lg">
            <div>
              {/* Navigation */}
              <nav className="flex flex-col space-y-2 p-4">
                  <NavLink
                      to="/dashboard/upload"
                      className={({ isActive }) =>
                          `flex items-center space-x-2 px-3 py-2 rounded-md hover:bg-gray-700 transition ${
                              isActive ? "bg-gray-700" : ""
                          }`
                      }
                  >
                      <FaFileUpload />
                      <span>Upload Policy</span>
                  </NavLink>

                  <NavLink
                      to="/dashboard/report"
                      className={({ isActive }) =>
                          `flex items-center space-x-2 px-3 py-2 rounded-md hover:bg-gray-700 transition ${
                              isActive ? "bg-gray-700" : ""
                          }`
                      }
                  >
                      <FaFileAlt />
                      <span>View Reports</span>
                  </NavLink>
              </nav>
            </div>

            {/* Footer */}
            <div className="text-center text-xs text-gray-400 py-4 border-t border-gray-700">
              <p>&copy; {new Date().getFullYear()} ComplyAI Inc.</p>
            </div>
        </aside>
    );
};

export default Sidebar;
