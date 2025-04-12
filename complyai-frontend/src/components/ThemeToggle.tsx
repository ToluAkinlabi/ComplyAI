// src/components/ThemeToggle.tsx

import { useEffect, useState } from "react";

const ThemeToggle = () => {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("theme") || "light";
    setEnabled(stored === "dark");
    document.documentElement.classList.toggle("dark", stored === "dark");
  }, []);

  const toggleTheme = () => {
    const next = !enabled;
    setEnabled(next);
    const theme = next ? "dark" : "light";
    localStorage.setItem("theme", theme);
    document.documentElement.classList.toggle("dark", next);
  };

  return (
    <div className="flex items-center gap-2 ml-4">
      
      <div
        onClick={toggleTheme}
        className={`w-12 h-6 flex items-center bg-gray-400 rounded-full cursor-pointer px-1 transition ${
          enabled ? "bg-green-500" : "bg-gray-400"
        }`}
      >
        <div
          className={`bg-white w-4 h-4 rounded-full shadow-md transform duration-300 ${
            enabled ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </div>
        <span className="text-sm text-gray-100 dark:text-gray-300">
            {enabled ? "🌙" : "☀️"}</span >
    </div>
  );
};

export default ThemeToggle;
