// src/dashboard/SavedResultsViewer.tsx

import { useState, useMemo } from "react";

interface SavedResultsViewerProps {
  executiveSummary: any;
  recommendations: any[];
}

const SavedResultsViewer = ({ executiveSummary, recommendations }: SavedResultsViewerProps) => {
  const [selectedFramework, setSelectedFramework] = useState<string>("All");

  const frameworkOptions = useMemo(() => {
    const unique = new Set(recommendations.map((r) => r.Framework || r.framework));
    return ["All", ...Array.from(unique)];
  }, [recommendations]);

  const filtered = useMemo(() => {
    return selectedFramework === "All"
      ? recommendations
      : recommendations.filter((r) => (r.Framework || r.framework) === selectedFramework);
  }, [selectedFramework, recommendations]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-1">Executive Summary</h2>
        <div className="bg-white p-4 rounded shadow">
          {Object.entries(executiveSummary).map(([key, value]) => (
            <p key={key}><strong>{key}:</strong> {value}</p>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Control Coverage</h2>
        <div>
          <label className="text-sm font-medium mr-2">Filter by Framework:</label>
          <select
            value={selectedFramework}
            onChange={(e) => setSelectedFramework(e.target.value)}
            className="border px-2 py-1 rounded text-sm"
          >
            {frameworkOptions.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      </div>

      <table className="table-auto w-full bg-white rounded shadow">
      <thead>
        <tr>
          <th className="border px-2 py-1">Status</th>
          <th className="border px-2 py-1">Framework</th>
          <th className="border px-2 py-1">Priority</th>
          <th className="border px-2 py-1">Sentence</th>
          <th className="border px-2 py-1">Suggestion</th>
        </tr>
      </thead>
      <tbody>
        {filtered.map((rec, i) => (
          <tr key={i}>
            <td className="border px-2 py-1">{rec.Status || rec.status}</td>
            <td className="border px-2 py-1">{rec.Framework || rec.framework}</td>
            <td className="border px-2 py-1">
              <span className={`text-xs font-semibold px-2 py-1 rounded-full
                ${
                  (rec.Priority || rec.priority) === "High"
                    ? "bg-red-100 text-red-700"
                    : (rec.Priority || rec.priority) === "Medium"
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-green-100 text-green-700"
                }`
              }>
                {rec.Priority || rec.priority}
              </span>
            </td>
            <td className="border px-2 py-1">{rec["Policy Sentence"]?.slice(0, 50)}...</td>
            <td className="border px-2 py-1">{rec["Suggested Improvement"]?.slice(0, 50) || "N/A"}...</td>
          </tr>
        ))}
      </tbody>
      </table>
    </div>
  );
};

export default SavedResultsViewer;
