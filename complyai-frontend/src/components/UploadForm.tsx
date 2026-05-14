import { useEffect, useState } from "react";
import Dropzone from "./Dropzone";
import { toast } from "react-hot-toast";
import { api, buildApiUrl } from "../api";

interface UploadFormProps {
    setFile: (file: File | null) => void;
    file: File | null;
    onUploadStart?: () => void;
    onUploadComplete?: (result: any) => void;
}

const UploadForm = ({ file, setFile, onUploadStart, onUploadComplete }: UploadFormProps) => {
  const [clientName, setClientName] = useState("");
  const [loading, setLoading] = useState(false);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkScreen = () => {
      setIsMobile(window.innerWidth < 640); // Tailwind's "sm" breakpoint
    };
    checkScreen();
    window.addEventListener("resize", checkScreen);
    return () => window.removeEventListener("resize", checkScreen);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (onUploadStart) {
      onUploadStart();
    }

    if (!file || !clientName.trim()) {
      toast.error("Please provide both the client name and a valid PDF file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("client_name", clientName.trim());

    try {
      setLoading(true);
      const res = await api.post("/upload-policy/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      if (res.status === 200 && res.data.report_url) {
        setReportUrl(buildApiUrl(res.data.report_url));
        toast.success("✅ Report generated successfully!");
        if (onUploadComplete) {
          onUploadComplete(res.data);
        }
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
    <div className="bg-white dark:bg-gray-800 dark:text-white p-6 md:p-8 rounded-lg shadow space-y-6 border border-gray-200 text-[10px] sm:text-xs">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-1">
          <label className="block font-medium">Client Name</label>
          <input
            type="text"
            className="w-full border rounded px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none text-gray-800"
            placeholder="e.g., Phillips Inc."
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
          />
        </div>

        {/* Dropzone on desktop, basic input on mobile */}
        {isMobile ? (
          <div>
            <label className="block font-medium mb-1">Upload PDF</label>
            <input
              type="file"
              accept=".pdf"
              title="Upload PDF file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full border rounded py-2 px-3 text-[14] file:bg-blue-600 file:text-white file:rounded file:border-none dark:text-gray-800"
            />
          </div>
        ) : (
          <Dropzone file={file} onFileAccepted={setFile} onRemoveFile={() => setFile(null)} />
        )}

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
