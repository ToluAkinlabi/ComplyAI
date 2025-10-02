import { useEffect, useState } from "react";
import axios from "axios";
import toast from "react-hot-toast";
import SavedResultsViewer from "./SavedResultsViewer";
import CompareModal from "../components/CompareModal";
import useIsMobile from "../hooks/useIsMobile";

interface DashboardSummary {
  total_reports: number;
  recent_reports: Array<{
    filename: string;
    client_name: string;
    document_name: string;
    generated_at: string;
    total_sentences: number;
    aligned_count: number;
    weak_count: number;
    missing_count: number;
    file_size: number;
    modified_date: string;
  }>;
  summary_stats: {
    total_policy_items: number;
    total_aligned: number;
    total_weak: number;
    total_missing: number;
    alignment_percentage: number;
    top_frameworks: Array<[string, number]>;
  };
}

const DashboardPage = () => {
  const isMobile = useIsMobile();
  
  // Updated state structure
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [availableReports, setAvailableReports] = useState<string[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [selectedView, setSelectedView] = useState<'overview' | 'detailed'>('overview');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError("");

      // Fetch dashboard summary and reports list
      const [summaryResponse, reportsListResponse] = await Promise.all([
        axios.get("http://localhost:8000/dashboard/summary"),
        axios.get("http://localhost:8000/list-json-reports/")
      ]);

      // Set dashboard data
      setSummary(summaryResponse.data);

      // Set available reports for comparison
      const reports = reportsListResponse.data.reports || [];
      const reportNames = reports.map((r: any) => r.name);
      setAvailableReports(reportNames);

      // Load latest report details for detailed view
      if (summaryResponse.data.recent_reports?.length > 0) {
        const latestReport = summaryResponse.data.recent_reports[0];
        try {
          const reportResponse = await axios.get(`http://localhost:8000/reports/${latestReport.filename}/json`);
          setData(reportResponse.data.detailed_report || []);
        } catch (reportErr) {
          console.warn("Could not load latest report details:", reportErr);
          setData([]);
        }
      } else {
        setData([]);
      }

    } catch (err: any) {
      console.error("Dashboard loading error:", err);
      if (err.code === 'ECONNREFUSED') {
        setError("Cannot connect to backend server. Please ensure the server is running on http://localhost:8000");
      } else {
        setError(err.response?.data?.detail || err.message || "Failed to load dashboard data");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRebuild = async () => {
    try {
      setRebuilding(true);
      const toastId = toast.loading("Rebuilding semantic index...");
      await axios.post("http://localhost:8000/rebuild-index/");
      toast.success("✅ Index rebuilt successfully!", { id: toastId });
      
      // Reload dashboard data after rebuild
      await loadDashboardData();
    } catch (err: any) {
      toast.error("❌ Failed to rebuild index");
      console.error(err);
    } finally {
      setRebuilding(false);
    }
  };

  const downloadCSV = async (reportFilename: string) => {
    try {
      const toastId = toast.loading("Downloading CSV...");
      const response = await axios.get(`http://localhost:8000/reports/${reportFilename}/csv`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', reportFilename.replace('.json', '.csv'));
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success("✅ CSV downloaded successfully!", { id: toastId });
    } catch (err: any) {
      toast.error("❌ Failed to download CSV");
      console.error(err);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (loading) {
    return (
      <div className="dark:bg-gray-800 text-gray-800 dark:text-white bg-gray-50 min-h-screen py-10 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dark:bg-gray-800 text-gray-800 dark:text-white bg-gray-50 min-h-screen py-10 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <div className="text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-800 rounded p-6 max-w-xl mx-auto">
              <strong>Error:</strong> {error}
              <button 
                onClick={loadDashboardData}
                className="block mt-4 mx-auto px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dark:bg-gray-800 text-gray-800 dark:text-white bg-gray-50 min-h-screen py-10 px-4 text-[10px] sm:text-xs">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl text-[20px] font-semibold">📊 ComplyAI Dashboard</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Comprehensive compliance analysis and reporting insights
            </p>
          </div>

          {/* View Toggle & Actions */}
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="flex bg-gray-200 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setSelectedView('overview')}
                className={`px-3 py-1 rounded text-sm transition ${
                  selectedView === 'overview' 
                    ? 'bg-white dark:bg-gray-600 shadow' 
                    : 'hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setSelectedView('detailed')}
                className={`px-3 py-1 rounded text-sm transition ${
                  selectedView === 'detailed' 
                    ? 'bg-white dark:bg-gray-600 shadow' 
                    : 'hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                Latest Report
              </button>
            </div>

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
        </div>

        {/* Dashboard Content */}
        {selectedView === 'overview' ? (
          summary && summary.total_reports > 0 ? (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-700 p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Total Reports</h3>
                <p className="text-3xl font-bold text-blue-600">{summary.total_reports}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Generated reports</p>
              </div>
              
              <div className="bg-white dark:bg-gray-700 p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Policy Items</h3>
                <p className="text-3xl font-bold text-green-600">{summary.summary_stats.total_policy_items}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Analyzed policies</p>
              </div>
              
              <div className="bg-white dark:bg-gray-700 p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Alignment</h3>
                <p className="text-3xl font-bold text-purple-600">{summary.summary_stats.alignment_percentage}%</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Overall compliance</p>
              </div>
              
              <div className="bg-white dark:bg-gray-700 p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">High Priority</h3>
                <p className="text-3xl font-bold text-red-600">{summary.summary_stats.total_missing}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Requires attention</p>
              </div>
            </div>

            {/* Status Breakdown & Top Frameworks */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-700 p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Policy Status Distribution</h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center">
                      <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
                      <span className="text-gray-700 dark:text-gray-300">Aligned</span>
                    </div>
                    <span className="font-bold text-green-600">{summary.summary_stats.total_aligned}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center">
                      <div className="w-3 h-3 bg-yellow-500 rounded-full mr-3"></div>
                      <span className="text-gray-700 dark:text-gray-300">Weak</span>
                    </div>
                    <span className="font-bold text-yellow-600">{summary.summary_stats.total_weak}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center">
                      <div className="w-3 h-3 bg-red-500 rounded-full mr-3"></div>
                      <span className="text-gray-700 dark:text-gray-300">Missing</span>
                    </div>
                    <span className="font-bold text-red-600">{summary.summary_stats.total_missing}</span>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-gray-700 p-6 rounded-lg shadow">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Top Frameworks</h3>
                <div className="space-y-3">
                  {summary.summary_stats.top_frameworks && summary.summary_stats.top_frameworks.slice(0, 5).map(([framework, count], index) => (
                    <div key={framework} className="flex justify-between items-center">
                      <div className="flex items-center">
                        <span className="text-sm bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded mr-3">
                          #{index + 1}
                        </span>
                        <span className="text-gray-700 dark:text-gray-300 truncate">{framework}</span>
                      </div>
                      <span className="font-bold text-blue-600 ml-2">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent Reports Table */}
            <div className="bg-white dark:bg-gray-700 rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-600">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Recent Reports</h3>
              </div>
              
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-600">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Client
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Document
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Generated
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Status Summary
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-700 divide-y divide-gray-200 dark:divide-gray-600">
                    {summary.recent_reports.map((report) => (
                      <tr key={report.filename} className="hover:bg-gray-50 dark:hover:bg-gray-600 transition">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                          {report.client_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                          <div>
                            <div className="truncate max-w-32">{report.document_name}</div>
                            <div className="text-xs text-gray-400">{formatFileSize(report.file_size)}</div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                          {new Date(report.generated_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex flex-wrap gap-1">
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200">
                              {report.aligned_count} ✓
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200">
                              {report.weak_count} ⚠
                            </span>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200">
                              {report.missing_count} ✗
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex gap-2">
                            <a
                              href={`http://localhost:8000/reports/${report.filename.replace('.json', '.pdf')}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 transition"
                            >
                              PDF
                            </a>
                            <button
                              onClick={() => downloadCSV(report.filename)}
                              className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300 transition"
                            >
                              CSV
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          ) : (
            /* Empty State for Overview */
            <div className="text-center py-16">
              <div className="bg-white dark:bg-gray-700 rounded-lg shadow-lg p-8 max-w-md mx-auto">
                <div className="text-6xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  No Reports Available
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                  Upload and analyze your first policy document to see compliance insights here.
                </p>
                <div className="space-y-3">
                  <a
                    href="/"
                    className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition font-medium"
                  >
                    📄 Upload Policy Document
                  </a>
                  <div>
                    <button 
                      onClick={loadDashboardData}
                      className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition text-sm"
                    >
                      🔄 Refresh Dashboard
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )
        ) : selectedView === 'detailed' ? (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Latest Report Details</h2>
            {data.length === 0 ? (
              <div className="text-center py-16">
                <div className="bg-white dark:bg-gray-700 rounded-lg shadow-lg p-8 max-w-md mx-auto">
                  <div className="text-6xl mb-4">📋</div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    No Report Details
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400 mb-6">
                    No detailed recommendations available. Generate a report first to see analysis details.
                  </p>
                  <a
                    href="/"
                    className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition font-medium"
                  >
                    📄 Upload Policy Document
                  </a>
                </div>
              </div>
            ) : (
              <SavedResultsViewer data={data} />
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400">No dashboard data available</p>
            <button 
              onClick={loadDashboardData}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
            >
              Reload Dashboard
            </button>
          </div>
        )}

        {/* Compare Modal */}
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