// src/dashboard/ReportComparison.tsx

import { useEffect, useState } from "react";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

interface Props {
  reports: string[];
}

const ReportComparison = ({ reports }: Props) => {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadAll = async () => {
      try {
        const fetched = await Promise.all(
          reports.map(async (filename) => {
            const res = await fetch(`http://localhost:8000/reports/${filename}`);
            const data = await res.json();
            return { name: filename, summary: data.executive_summary };
          })
        );
        setResults(fetched);
      } catch (err) {
        console.error("Failed to load reports", err);
      } finally {
        setLoading(false);
      }
    };

    loadAll();
  }, [reports]);

  if (loading) return <p className="text-gray-500">Loading comparison...</p>;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {results.map((report) => {
        const summary = report.summary || {};
        const chartData = {
          labels: ["Aligned", "Weak", "Missing"],
          datasets: [
            {
              data: [
                summary.Aligned || summary.status_counts?.Aligned || 0,
                summary.Weak || summary.status_counts?.Weak || 0,
                summary.Missing || summary.status_counts?.Missing || 0
              ],
              backgroundColor: ["#16a34a", "#eab308", "#dc2626"],
              borderWidth: 1
            }
          ]
        };

        return (
          <div key={report.name} className="bg-white dark:bg-gray-800 text-gray-800 dark:text-white p-4 rounded shadow space-y-2">
            <h3 className="font-semibold text-sm truncate" title={report.name}>
              {report.name}
            </h3>
            <div className="text-xs text-gray-600 space-y-1">
              <p>Total: {summary["Total Sentences"] || summary.total_sentences_analyzed}</p>
              <p>Aligned: {summary.Aligned || summary.status_counts?.Aligned || 0}</p>
              <p>Weak: {summary.Weak || summary.status_counts?.Weak || 0}</p>
              <p>Missing: {summary.Missing || summary.status_counts?.Missing || 0}</p>
            </div>
            <div className="w-40 mx-auto">
              <Pie data={chartData} />
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ReportComparison;
