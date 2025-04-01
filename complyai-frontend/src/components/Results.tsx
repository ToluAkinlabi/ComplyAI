interface ResultsProps {
    executiveSummary: any;
    recommendations: any[];
}

const Results = ({ executiveSummary, recommendations }: ResultsProps) => {
    if (!executiveSummary || !recommendations) return null;

    return (
        <div className="mt-6 space-y-4">
            <h2 className="text-xl font-semibold">Executive Summary</h2>
            <div className="bg-white p-4 rounded shadow">
                {Object.entries(executiveSummary).map(([key, value]) => (
                    <p key={key}><strong>{key}:</strong> {value}</p>
                ))}
            </div>

            <h2 className="text-xl font-semibold mt-4">Recommendations</h2>
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
                {recommendations.map((rec, i) => (
                    <tr key={i}>
                        <td className="border px-2 py-1">{rec.status || "N/A"}</td>
                        <td className="border px-2 py-1">{rec.framework || "N/A"}</td>
                        <td className="border px-2 py-1">{rec.policy_sentence ? rec.policy_sentence.slice(0, 50) + "..." : "N/A"}</td>
                        <td className="border px-2 py-1">{rec.suggested_statement ? rec.suggested_statement.slice(0, 50) + "..." : "N/A"}</td>
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    );
};

export default Results;
