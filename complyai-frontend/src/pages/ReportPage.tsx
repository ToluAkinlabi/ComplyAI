// src/pages/ReportPage.tsx

import { useEffect, useMemo, useState } from "react";
import { FiTrash2, FiDownload } from "react-icons/fi";
import toast from "react-hot-toast";
import { api, buildApiUrl } from "../api";

interface ReportHistoryItem {
  id: number;
  report_file_name: string | null;
  json_file_name: string | null;
  client_name: string;
  document_name: string;
  status: string;
  created_at: string | null;
  file_size: number | null;
}

interface ReportHistoryResponse {
  items: ReportHistoryItem[];
  pagination: {
    limit: number;
    offset: number;
    total: number;
    has_more: boolean;
  };
}

const PAGE_SIZE = 12;

const ReportPage = () => {
  const [reports, setReports] = useState<ReportHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    fetchReports();
  }, [page, search, statusFilter]);

  const fetchReports = async () => {
    try {
      setLoading(true);
      const offset = (page - 1) * PAGE_SIZE;
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset,
      };

      if (search.trim()) {
        params.search = search.trim();
      }

      if (statusFilter) {
        params.status = statusFilter;
      }

      const res = await api.get<ReportHistoryResponse>("/reports/history", { params });
      setReports(res.data.items || []);
      setTotal(res.data.pagination?.total || 0);
    } catch (error) {
      console.error("Failed to fetch report history", error);
      toast.error("Failed to load report history");
      setReports([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(query);
  };

  const handleDelete = (reportName: string) => {
    toast.custom((t) => (
      <div className={`bg-white dark:bg-gray-900 text-gray-800 dark:text-white border rounded-lg shadow-xl p-5 w-80 ${t.visible ? "animate-enter" : "animate-leave"}`}>
        <h4 className="text-sm font-semibold text-gray-800 mb-1">Delete Report?</h4>
        <p className="text-xs">
          Are you sure you want to delete <span className="font-medium text-red-600">{reportName}</span>? This action cannot be undone.
        </p>

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
                await api.delete(`/delete-report/${reportName}`);
                toast.success("Report deleted!", { duration: 3000 });
                await fetchReports();
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

  const formatDate = (isoDate: string | null) => {
    if (!isoDate) return "Unknown";
    return new Date(isoDate).toLocaleString();
  };

  const formatFileSize = (bytes: number | null) => {
    const value = bytes || 0;
    if (value <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
    const size = value / Math.pow(1024, index);
    return `${size.toFixed(2)} ${units[index]}`;
  };

  return (
    <div className="dark:bg-gray-800 text-gray-900 dark:text-white space-y-6">
      <div>
        <h1 className="text-2xl text-[20px] font-semibold mb-1">📄 Generated Reports</h1>
        <p className="text-sm text-[11px]">Download or manage your compliance reports.</p>
      </div>

      <form onSubmit={handleSearchSubmit} className="bg-white dark:bg-gray-700 p-4 rounded-lg shadow border flex flex-col md:flex-row gap-3 md:items-end">
        <div className="flex-1">
          <label className="block text-xs mb-1">Search</label>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by client, document, or filename"
            className="w-full border rounded px-3 py-2 text-sm text-gray-800"
          />
        </div>
        <div>
          <label className="block text-xs mb-1">Status</label>
          <select
            title="Filter reports by status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="border rounded px-3 py-2 text-sm text-gray-800"
          >
            <option value="">All</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
          </select>
        </div>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition">
          Apply
        </button>
      </form>

      {loading ? (
        <div className="text-center text-[12px] text-gray-500 py-10">⏳ Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="text-center text-[12px] text-gray-400 italic py-10">No reports found for this filter.</div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {reports.map((report) => {
              const downloadName = report.report_file_name || report.json_file_name;
              return (
                <div
                  key={`${report.id}-${downloadName}`}
                  className="flex flex-col justify-between bg-white p-4 rounded-lg shadow border hover:border-blue-400 transition-all space-y-2"
                >
                  <div>
                    <h3 className="font-medium text-[14px] truncate text-gray-800" title={downloadName || "unknown"}>
                      {downloadName || "Unknown artifact"}
                    </h3>
                    <p className="text-xs text-[10px] text-gray-500">Client: {report.client_name || "Unknown"}</p>
                    <p className="text-xs text-[10px] text-gray-500">Document: {report.document_name || "Unknown"}</p>
                    <p className="text-xs text-[10px] text-gray-500">Status: {report.status}</p>
                    <p className="text-xs text-[10px] text-gray-500">Created: {formatDate(report.created_at)}</p>
                    <p className="text-xs text-[10px] text-gray-500">Size: {formatFileSize(report.file_size)}</p>
                  </div>
                  <div className="flex justify-between items-center text-sm pt-2 border-t">
                    {downloadName ? (
                      <a
                        href={buildApiUrl(`/reports/${downloadName}`)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center space-x-1 text-blue-600 hover:underline"
                      >
                        <FiDownload size={14} /> <span className="text-[12px]">Download</span>
                      </a>
                    ) : (
                      <span className="text-[12px] text-gray-400">Unavailable</span>
                    )}
                    {downloadName ? (
                      <button
                        onClick={() => handleDelete(downloadName)}
                        className="flex items-center space-x-1 text-red-600 hover:underline"
                      >
                        <FiTrash2 size={14} /> <span className="text-[12px]">Delete</span>
                      </button>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between bg-white dark:bg-gray-700 p-3 rounded border">
            <p className="text-xs text-gray-600 dark:text-gray-200">
              Showing {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, total)} of {total}
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                className="px-3 py-1 text-xs border rounded disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-xs">Page {page} / {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                className="px-3 py-1 text-xs border rounded disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportPage;
