import { useState } from "react";
import axios from "axios";
import Results from "./Results";

const UploadForm = () => {
  const [clientName, setClientName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [executiveSummary, setExecutiveSummary] = useState<null | object>(null);
  const [recommendations, setRecommendations] = useState<null | any[]>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();  

    if (!file || !clientName) {
        alert("Please provide both client name and a policy file.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("client_name", clientName);

    try {
        setLoading(true);
        const res = await axios.post("http://localhost:8000/upload-policy/", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });

        setExecutiveSummary(res.data.executive_summary);
        setRecommendations(res.data.detailed_report);
    } catch (error) {
        console.error(error);
        alert("Error generating report. Check console.");
    } finally {
        setLoading(false);
    }
}

  return (
    <div className="max-w-md mx-auto bg-white p-6 rounded shadow-md space-y-4">
      <h2 className="text-xl font-semibold">Upload Policy for Compliance Assessment</h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block font-medium">Client Name</label>
          <input
            type="text"
            className="w-full border rounded p-2"
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            placeholder="e.g., Phillips Inc."
          />
        </div>
        <div>
          <label className="block font-medium">Policy Document (PDF)</label>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Processing..." : "Generate Report"}
        </button>
      </form>

      {/* Only renders when data is available */}
      {executiveSummary && recommendations && (
        <Results executiveSummary={executiveSummary} recommendations={recommendations} />
      )}
    </div>
  );
};

export default UploadForm;
