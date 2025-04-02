// src/components/UploadForm.tsx

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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!file || !clientName.trim()) {
            alert("Please provide both the client name and a valid PDF file.");
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
                toast.success("Report generated successfully! Opening PDF...");
    
                // Automatically open the PDF report in a new tab
                window.open(res.data.report_url, "_blank");
            } else {
                toast.error("Report generated, but no PDF was returned.");
            }
    
        } catch (error: any) {
            console.error("Upload failed:", error);
            toast.error(`❌ Error generating report: ${error.message || "Unknown error"}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow-lg space-y-6">
            <h2 className="text-2xl font-semibold text-center">Generate Compliance Report</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block font-medium mb-1">Client Name</label>
                    <input
                        type="text"
                        className="w-full border rounded px-3 py-2 focus:ring focus:ring-blue-300"
                        placeholder="e.g., Phillips Inc."
                        value={clientName}
                        onChange={(e) => setClientName(e.target.value)}
                    />
                </div>
                <Dropzone 
                    file={file} 
                    onFileAccepted={setFile} 
                    onRemoveFile={() => setFile(null)} 
                />
                <button
                    type="submit"
                    disabled={loading}
                    className="bg-blue-600 w-full text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 transition"
                >
                    {loading ? "Processing..." : "Generate Report"}
                </button>
            </form>
        </div>
    );
};

export default UploadForm;
