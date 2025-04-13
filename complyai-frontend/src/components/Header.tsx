// src/components/Header.tsx
import MobileSidebarToggle from "./MobileSidebarToggle";

interface HeaderProps {
  setSidebarOpen: (open: boolean) => void;
}

const Header = ({ setSidebarOpen }: HeaderProps) => {
  return (
    <header className="bg-white dark:bg-gray-900 text-gray-800 dark:text-white shadow-md px-6 py-3 flex items-center justify-between sticky fixed top-0 left-0 right-0 z-50 text-[10px] sm:text-xs">
      <div className="flex items-center gap-2">

        {/* Hamburger only shows on mobile */}
        <MobileSidebarToggle onToggle={() => setSidebarOpen(true)} />
        <img src="/C.png" alt="ComplyAI Logo" className="h-10 w-auto" />
        <h1 className="text-[13px] font-semibold">Dashboard</h1>
      </div>

      <div className="flex items-center space-x-4 text-sm">
        <span className="text-[13px]">Welcome, <strong>Auditor</strong></span>
        <button className="text-blue-600 text-[13px] hover:underline">Logout</button>
      </div>
    </header>
  );
};

export default Header;
