// src/dashboard/DashboardPage.tsx

import { useEffect, useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import SavedResultsViewer from "./SavedResultsViewer";
import CompareModal from "../components/CompareModal";
import useIsMobile from "../hooks/useIsMobile"; 

const DashboardPage = () => {
  const isMobile = useIsMobile(); 
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [availableReports, setAvailableReports] = useState<string[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);

  useEffect(() => {
    const loadInitial = async () => {
      try {
        const listRes = await axios.get("http://localhost:8000/list-json-reports/");
        const reports = listRes.data.reports || [];
        const names = reports.map((r: any) => r.name);
        setAvailableReports(names);

        if (names.length === 0) throw new Error("No reports found.");

        const latestReport = names[0];
        const reportRes = await fetch(`http://localhost:8000/reports/${latestReport}`);
        if (!reportRes.ok) throw new Error("Failed to fetch latest report");

        const reportData = await reportRes.json();
        setData(reportData.detailed_report || []);
      } catch (err: any) {
        setError(err.message || "Something went wrong.");
      } finally {
        setLoading(false);
      }
    };

    loadInitial();
  }, []);

  const handleRebuild = async () => {
    try {
      setRebuilding(true);
      const toastId = toast.loading("Rebuilding semantic index...");
      await axios.post("http://localhost:8000/rebuild-index/");
      toast.success("✅ Index rebuilt successfully!", { id: toastId });
    } catch (err: any) {
      toast.error("❌ Failed to rebuild index");
      console.error(err);
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="dark:bg-gray-800 text-gray-800 dark:text-white bg-gray-50 py-10 px-4 text-[10px] sm:text-xs">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl text-[20px] font-semibold">📊 Compliance Dashboard</h1>
            <p className="text-sm">Explore and compare insights from your reports.</p>
          </div>

          {/* Hide buttons on mobile */}
          {!isMobile && (
            <div className="flex gap-2">
              <button
                onClick={() => setIsModalOpen(true)}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition text-sm"
              >
                Compare Reports
              </button>

              {import.meta.env.VITE_IS_ADMIN_UI === "true" && (
                <button
                  onClick={handleRebuild}
                  disabled={rebuilding}
                  className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-700 transition text-sm disabled:opacity-50"
                >
                  {rebuilding ? "Rebuilding..." : "Rebuild Index"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Body */}
        {loading ? (
          <p className="text-gray-500 text-center mt-10">⏳ Loading latest report...</p>
        ) : error ? (
          <div className="text-red-600 bg-red-50 border border-red-300 rounded p-4 text-center max-w-xl mx-auto">
            <strong>Error:</strong> {error}
          </div>
        ) : data.length === 0 ? (
          <p className="text-gray-400 italic text-center mt-10">
            No recommendations available in the latest report.
          </p>
        ) : (
          <SavedResultsViewer data={data} />
        )}

        {/* Modal */}
        <CompareModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          reportNames={availableReports}
        />
      </div>
    </div>
  );
};

export default DashboardPage;
