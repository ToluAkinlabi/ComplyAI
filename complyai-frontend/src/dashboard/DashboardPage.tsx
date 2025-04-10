// src/dashboard/DashboardPage.tsx

import { useEffect, useState } from "react";
import axios from "axios";
import SavedResultsViewer from "./SavedResultsViewer";

interface ReportInfo {
  name: string;
  modified: number;
}

const DashboardPage = () => {
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [reportData, setReportData] = useState<any>(null);

  useEffect(() => {
    fetchReportList();
  }, []);

  const fetchReportList = async () => {
    try {
      const res = await axios.get("http://localhost:8000/list-json-reports/");
      setReports(res.data.reports);
    } catch (err) {
      console.error("Error loading report list:", err);
    }
  };

  const loadReport = async (name: string) => {
    try {
      const res = await axios.get(`http://localhost:8000/reports/${name}`);
      setReportData(res.data);
      setSelectedReport(name);
    } catch (err) {
      console.error("Error loading report data:", err);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">📊 Compliance Dashboard</h1>
      <p className="text-gray-600">Click a report to view its detailed controls and compliance status.</p>

      <div className="flex flex-wrap gap-4">
        {reports.map((r) => (
          <button
            key={r.name}
            onClick={() => loadReport(r.name)}
            className={`px-4 py-2 rounded border shadow ${
              selectedReport === r.name ? "bg-blue-600 text-white" : "bg-white text-gray-700"
            }`}
          >
            {r.name.replace(".json", "")}
          </button>
        ))}
      </div>

      {reportData && (
        <div className="mt-6">
          <SavedResultsViewer executiveSummary={reportData.executive_summary} recommendations={reportData.detailed_report} />
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
