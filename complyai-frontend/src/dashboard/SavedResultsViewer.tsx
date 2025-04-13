import { useState, useRef } from "react";
import { Pie } from "react-chartjs-2";
import { saveAs } from "file-saver";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

interface SavedResultsViewerProps {
  data: any[];
}

const PAGE_SIZE = 10;

const SavedResultsViewer = ({ data }: SavedResultsViewerProps) => {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("All");
  const [framework, setFramework] = useState("All");
  const [page, setPage] = useState(1);
  const chartRef = useRef<any>(null);

  const priorities = ["All", "High", "Medium", "Low"];
  const frameworks = Array.from(new Set(data.map((r) => r.Framework || r.framework)));

  const filtered = data.filter((r) => {
    const sentence = r["Policy Sentence"]?.toLowerCase() || "";
    const suggestion = r["Suggested Improvement"]?.toLowerCase() || "";
    const matchesSearch = sentence.includes(search.toLowerCase()) || suggestion.includes(search.toLowerCase());
    const matchesPriority = priority === "All" || (r.Priority || r.priority) === priority;
    const matchesFramework = framework === "All" || (r.Framework || r.framework) === framework;
    return matchesSearch && matchesPriority && matchesFramework;
  });

  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: "application/json" });
    saveAs(blob, "filtered_report.json");
  };

  const exportCSV = () => {
    const headers = ["Status", "Framework", "Priority", "Policy Sentence", "Suggested Improvement"];
    const rows = filtered.map((r) =>
      [r.Status, r.Framework, r.Priority, r["Policy Sentence"], r["Suggested Improvement"]].map((v) =>
        `${v}`.replace(/"/g, '""')
      )
    );
    const csv = [headers, ...rows].map((r) => r.map((v) => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    saveAs(blob, "filtered_report.csv");
  };

  const handleDownloadChart = () => {
    const chart = chartRef.current;
    const canvas = chart?.canvas;
    if (!canvas) return;
    canvas.toBlob((blob: any) => {
      if (blob) saveAs(blob, "complyai_summary_chart.png");
    });
  };

  const priorityBadge = (p: string) => {
    const base = "text-xs font-semibold px-2 py-1 rounded-full";
    if (p === "High") return <span className={`${base} bg-red-700 text-white`}>High</span>;
    if (p === "Medium") return <span className={`${base} bg-yellow-400 text-black`}>Medium</span>;
    if (p === "Low") return <span className={`${base} bg-green-700 text-white`}>Low</span>;
    return <span className={base}>N/A</span>;
  };

  const total = filtered.length;
  const statusCounts = {
    Aligned: filtered.filter((r) => (r.Status || r.status) === "Aligned").length,
    Weak: filtered.filter((r) => (r.Status || r.status) === "Weak").length,
    Missing: filtered.filter((r) => (r.Status || r.status) === "Missing").length,
  };

  const chartData = {
    labels: ["Aligned", "Weak", "Missing"],
    datasets: [
      {
        data: [statusCounts.Aligned, statusCounts.Weak, statusCounts.Missing],
        backgroundColor: ["#22c55e", "#eab308", "#dc2626"],
        borderWidth: 1,
      },
    ],
  };

  return (
    <div className="space-y-6 text-gray-800 dark:text-gray-200 text-[10px] sm:text-xs">

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded shadow-md space-y-4">
        <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-4">
          <input
            type="text"
            className="border dark:border-gray-600 rounded px-3 py-2 w-full sm:w-60 dark:bg-gray-800 dark:text-white"
            placeholder="Search policy or suggestion..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          <select className="border dark:border-gray-600 rounded px-3 py-2 dark:bg-gray-800 dark:text-white" value={priority} onChange={(e) => setPriority(e.target.value)}>
            {priorities.map((p) => <option key={p}>{p}</option>)}
          </select>
          <select className="border dark:border-gray-600 rounded px-3 py-2 dark:bg-gray-800 dark:text-white" value={framework} onChange={(e) => setFramework(e.target.value)}>
            <option>All</option>
            {frameworks.map((f) => <option key={f}>{f}</option>)}
          </select>
          <div className="flex flex-wrap justify-start sm:ml-auto gap-2">
            <button onClick={exportJSON} className="text-sm px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
              Export JSON
            </button>
            <button onClick={exportCSV} className="text-sm px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700">
              Export CSV
            </button>
          </div>
        </div>

        {/* Legend */}
        <div className="text-sm flex gap-4 mt-3 text-[10px] sm:text-xs">
          <span className="flex items-center gap-1"><span className="inline-block w-4 h-4 rounded-full bg-red-700"></span> High</span>
          <span className="flex items-center gap-1"><span className="inline-block w-4 h-4 rounded-full bg-yellow-400"></span> Medium</span>
          <span className="flex items-center gap-1"><span className="inline-block w-4 h-4 rounded-full bg-green-700"></span> Low</span>
        </div>
      </div>

      {/* Chart + Summary */}
      <div className="bg-white dark:bg-gray-800 p-4 rounded shadow-md space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-md font-semibold">Summary</h2>
          <button onClick={handleDownloadChart} className="text-sm text-blue-600 hover:underline dark:text-blue-400">
            Download Chart
          </button>
        </div>
        <div className="flex flex-wrap gap-6 items-center">
          <div className="space-y-1 text-sm">
            <p>Total: <strong>{total}</strong></p>
            <p>Aligned: <strong>{statusCounts.Aligned}</strong></p>
            <p>Weak: <strong>{statusCounts.Weak}</strong></p>
            <p>Missing: <strong>{statusCounts.Missing}</strong></p>
          </div>
          <div className="w-48">
            <Pie ref={chartRef} data={chartData} />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto bg-white dark:bg-gray-800 rounded shadow-md">
        <table className="table-auto w-full text-sm">
          <thead className="bg-gray-100 dark:bg-gray-700 text-left">
            <tr>
              <th className="px-3 py-2 border dark:border-gray-700">Status</th>
              <th className="px-3 py-2 border dark:border-gray-700">Framework</th>
              <th className="px-3 py-2 border dark:border-gray-700">Priority</th>
              <th className="px-3 py-2 border dark:border-gray-700">Policy Sentence</th>
              <th className="px-3 py-2 border dark:border-gray-700">Suggested Improvement</th>
            </tr>
          </thead>
          <tbody>
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center text-gray-400 dark:text-gray-500 py-10">
                  No results found.
                </td>
              </tr>
            ) : (
              paginated.map((rec, i) => (
                <tr key={i} className="border-t dark:border-gray-700">
                  <td className="px-3 py-2 border dark:border-gray-700">{rec.Status || rec.status}</td>
                  <td className="px-3 py-2 border dark:border-gray-700">{rec.Framework || rec.framework}</td>
                  <td className="px-3 py-2 border dark:border-gray-700">{priorityBadge(rec.Priority || rec.priority)}</td>
                  <td className="px-3 py-2 border dark:border-gray-700">{(rec["Policy Sentence"] || "").slice(0, 80)}...</td>
                  <td className="px-3 py-2 border dark:border-gray-700">{(rec["Suggested Improvement"] || "N/A").slice(0, 80)}...</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-center items-center dark:bg-gray-800 text-gray-800 dark:text-white space-x-4 mt-4">
        <button className="px-3 py-1 text-sm border rounded disabled:opacity-30" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</button>
        <span className="text-sm">Page {page} of {totalPages}</span>
        <button className="px-3 py-1 text-sm border rounded disabled:opacity-30" disabled={page === totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>Next</button>
      </div>
    </div>
  );
};

export default SavedResultsViewer;
