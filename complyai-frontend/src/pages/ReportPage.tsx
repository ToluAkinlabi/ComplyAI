// src/pages/ReportPage.tsx

import { useEffect, useState } from "react";
import axios from "axios";

interface Report {
  name: string;
  modified: number;
}

const ReportPage = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const res = await axios.get("http://localhost:8000/list-reports/");
        setReports(res.data.reports);
      } catch (error) {
        console.error("Failed to fetch reports", error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">📄 Generated Compliance Reports</h1>

      {loading ? (
        <div className="text-center text-gray-500 animate-pulse">⏳ Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="text-center text-gray-400 italic">No reports available yet. Generate one from the upload page.</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <div
              key={report.name}
              className="bg-white p-4 rounded-lg border shadow-sm hover:shadow-md transition cursor-pointer flex flex-col justify-between"
            >
              <div>
                <h3 className="font-medium text-lg truncate">{report.name}</h3>
                <p className="text-xs text-gray-500">Last Modified: {formatDate(report.modified)}</p>
              </div>
              <a
                href={`http://localhost:8000/reports/${report.name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-block text-sm text-blue-600 hover:underline"
              >
                ⬇ Download PDF
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReportPage;
