// src/dashboard/DashboardPage.tsx

import { useEffect, useState } from "react";
import SavedResultsViewer from "./SavedResultsViewer";

const DashboardPage = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadLatestReport = async () => {
      try {
        const listRes = await fetch("http://localhost:8000/list-json-reports/");
        const listData = await listRes.json();

        if (!listData.reports || listData.reports.length === 0) {
          throw new Error("No reports found.");
        }

        const latestReport = listData.reports[0].name;
        const reportRes = await fetch(`http://localhost:8000/reports/${latestReport}`);

        if (!reportRes.ok) throw new Error("Failed to fetch report file");

        const reportData = await reportRes.json();
        setData(reportData.detailed_report || []);
      } catch (err: any) {
        setError(err.message || "Something went wrong.");
      } finally {
        setLoading(false);
      }
    };

    loadLatestReport();
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold mb-2">📊 Compliance Dashboard</h1>

      {loading ? (
        <p className="text-gray-500">Loading report...</p>
      ) : error ? (
        <div className="text-red-600 bg-red-50 border border-red-300 rounded p-3">
          <strong>Error:</strong> {error}
        </div>
      ) : data.length === 0 ? (
        <p className="text-gray-400 italic">No recommendations available in the latest report.</p>
      ) : (
        <SavedResultsViewer data={data} />
      )}
    </div>
  );
};

export default DashboardPage;
