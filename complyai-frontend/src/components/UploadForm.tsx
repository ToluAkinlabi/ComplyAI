import axios from "axios";
import { useState } from "react";
import Dropzone from "./Dropzone";
import { toast } from "react-hot-toast";

interface UploadFormProps {
  file: File | null;
  setFile: (file: File | null) => void;
}

const UploadForm = ({ file, setFile }: UploadFormProps) => {
  const [clientName, setClientName] = useState("");
  const [loading, setLoading] = useState(false);
  const [reportUrl, setReportUrl] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file || !clientName.trim()) {
      toast.error("Please provide both the client name and a valid PDF file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("client_name", clientName.trim());

    try {
      setLoading(true);

      const res = await axios.post("http://localhost:8000/upload-policy/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (res.status === 200 && res.data.report_url) {
        setReportUrl(res.data.report_url);
        toast.success("✅ Report generated successfully!");
      } else {
        toast.error("⚠️ Report generated, but no PDF returned.");
      }
    } catch (error: any) {
      console.error("Upload failed:", error);
      toast.error(`Error: ${error.message || "Unknown error"}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 md:p-8 rounded-lg shadow space-y-6 border border-gray-200">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1">
          <label className="block font-medium text-gray-700">Client Name</label>
          <input
            type="text"
            className="w-full border rounded px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="e.g., Phillips Inc."
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
          />
        </div>

        <Dropzone file={file} onFileAccepted={setFile} onRemoveFile={() => setFile(null)} />

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition disabled:opacity-50 font-medium"
        >
          {loading ? "Processing..." : "Generate Report"}
        </button>
      </form>

      {reportUrl && (
        <div className="mt-4 flex flex-col sm:flex-row sm:justify-between items-center gap-2 bg-gray-50 border p-4 rounded shadow-sm">
          <a
            href={reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline font-medium"
          >
            View Report
          </a>
          <a
            href={reportUrl}
            download
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm"
          >
            Download PDF
          </a>
          <button
            onClick={() => {
              navigator.clipboard.writeText(reportUrl);
              toast.success("Link copied to clipboard!");
            }}
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm px-3 py-1 rounded"
          >
            Copy Link
          </button>
        </div>
      )}
    </div>
  );
};

export default UploadForm;
