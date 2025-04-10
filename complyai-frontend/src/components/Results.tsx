// Results.tsx

import { useState, useMemo } from "react";

interface ResultsProps {
    executiveSummary: any;
    recommendations: any[];
}

const Results = ({ executiveSummary, recommendations }: ResultsProps) => {
    const [selectedFramework, setSelectedFramework] = useState<string>("All");

    if (!executiveSummary || !recommendations) return null;

    const frameworkOptions = useMemo(() => {
        const unique = new Set(recommendations.map((r) => r.framework));
        return ["All", ...Array.from(unique)];
    }, [recommendations]);

    const filteredRecommendations = useMemo(() => {
        return selectedFramework === "All"
            ? recommendations
            : recommendations.filter((r) => r.framework === selectedFramework);
    }, [selectedFramework, recommendations]);

    return (
        <div className="mt-6 space-y-6">
            <div>
                <h2 className="text-xl font-semibold mb-1">Executive Summary</h2>
                <div className="bg-white p-4 rounded shadow">
                    {Object.entries(executiveSummary).map(([key, value]) => (
                        <p key={key}><strong>{key}:</strong> {value}</p>
                    ))}
                </div>
            </div>

            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Control Coverage Report</h2>
                <div>
                    <label className="text-sm font-medium mr-2">Filter by Framework:</label>
                    <select
                        value={selectedFramework}
                        onChange={(e) => setSelectedFramework(e.target.value)}
                        className="border rounded px-2 py-1 text-sm"
                    >
                        {frameworkOptions.map((fw) => (
                            <option key={fw} value={fw}>{fw}</option>
                        ))}
                    </select>
                </div>
            </div>

            <table className="table-auto w-full bg-white rounded shadow">
                <thead>
                    <tr>
                        <th className="border px-2 py-1">Status</th>
                        <th className="border px-2 py-1">Framework</th>
                        <th className="border px-2 py-1">Sentence</th>
                        <th className="border px-2 py-1">Suggestion</th>
                    </tr>
                </thead>
                <tbody>
                    {filteredRecommendations.map((rec, i) => (
                        <tr key={i}>
                            <td className="border px-2 py-1">{rec.status || "N/A"}</td>
                            <td className="border px-2 py-1">{rec.framework || "N/A"}</td>
                            <td className="border px-2 py-1">{rec.policy_sentence?.slice(0, 50) || "N/A"}...</td>
                            <td className="border px-2 py-1">{rec.suggested_statement?.slice(0, 50) || "N/A"}...</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default Results;
