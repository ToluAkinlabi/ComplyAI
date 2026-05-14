// src/pages/ReportPage.tsx

import { useEffect, useState } from "react";
import { FiTrash2, FiDownload } from "react-icons/fi";
import toast from "react-hot-toast"; 
import { api, buildApiUrl } from "../api";

interface Report {
    name: string;
    modified: number;
}

// ReportPage component to display and manage generated reports
const ReportPage = () => {
    const [reports, setReports] = useState<Report[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchReports();
    }, []);

    // Fetch reports from the server
    const fetchReports = async () => {
        try {
            const res = await api.get("/list-reports/");
            setReports(res.data.reports);
        } catch (error) {
            console.error("Failed to fetch reports", error);
        } finally {
            setLoading(false);
        }
    };

    // Function to handle deletion of a report
    const handleDelete = (name: string) => {
      toast.custom((t) => (
          <div className={`bg-white dark:bg-gray-900 text-gray-800 dark:text-white border rounded-lg shadow-xl p-5 w-80 ${t.visible ? 'animate-enter' : 'animate-leave'}`}>
              <h4 className="text-sm font-semibold text-gray-800 mb-1">Delete Report?</h4>
              <p className="text-xs">Are you sure you want to delete <span className="font-medium text-red-600">{name}</span>? This action cannot be undone.</p>
              
              <div className="flex justify-end gap-2 mt-4">
                  <button
                      onClick={() => toast.dismiss(t.id)}
                      className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-50 transition"
                  >
                      Cancel
                  </button>
                  <button
                      onClick={async () => {
                          toast.dismiss(t.id);
                          try {
                              await api.delete(`/delete-report/${name}`);
                              setReports(reports.filter((r) => r.name !== name));
                              toast.success("Report deleted!", { duration: 3000 });
                          } catch {
                              toast.error("Failed to delete report");
                          }
                      }}
                      className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition"
                  >
                      Confirm Delete
                  </button>
              </div>
          </div>
      ));
    };

    // Format date from timestamp
    const formatDate = (timestamp: number) => {
        return new Date(timestamp * 1000).toLocaleString();
    };

    // Render the component
    return (
        <div className="dark:bg-gray-800 text-gray-900 dark:text-white space-y-6">
            <div>
                <h1 className="text-2xl text-[20px] font-semibold mb-1">📄 Generated Reports</h1>
                <p className="text-sm text-[11px]">Download or manage your compliance reports.</p>
            </div>

            {loading ? (
                <div className="text-center text-[12px] text-gray-500 py-10">⏳ Loading reports...</div>
            ) : reports.length === 0 ? (
                <div className="text-center text-[12px] text-gray-400 italic py-10">No reports available yet. Generate one from the upload page.</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {reports.map((report) => (
                        <div
                            key={report.name}
                            className="flex flex-col justify-between bg-white p-4 rounded-lg shadow border hover:border-blue-400 transition-all space-y-2"
                        >
                            <div>
                                <h3 className="font-medium text-[14px] truncate text-gray-800" title={report.name}>{report.name}</h3>
                                <p className="text-xs text-[10px] text-gray-500">Last Modified: {formatDate(report.modified)}</p>
                            </div>
                            <div className="flex justify-between items-center text-sm pt-2 border-t">
                                <a
                                    href={buildApiUrl(`/reports/${report.name}`)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center space-x-1 text-blue-600 hover:underline"
                                >
                                    <FiDownload size={14} /> <span className="text-[12px]">Download</span>
                                </a>
                                <button
                                    onClick={() => handleDelete(report.name)}
                                    className="flex items-center space-x-1 text-red-600 hover:underline"
                                >
                                    <FiTrash2 size={14} /> <span className="text-[12px]">Delete</span>
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ReportPage;
