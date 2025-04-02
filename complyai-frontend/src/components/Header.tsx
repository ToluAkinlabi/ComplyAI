// src/components/Header.tsx

const Header = () => {
    return (
        <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-50">
            <div>
                <img src="/C.png" alt="ComplyAI Logo" className="h-12
               w-auto" />
                <h1 className="text-lg font-semibold text-gray-800">Dashboard</h1>
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span>Welcome, <strong>Auditor</strong></span>
                <button className="text-blue-600 hover:underline">Logout</button>
            </div>
        </header>
    );
};

export default Header;
