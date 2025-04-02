// src/components/PDFPreview.tsx

import { useState } from "react";

interface PDFPreviewProps {
    file: File | null;
    onRemoveFile: () => void;
}

const PDFPreview = ({ file, onRemoveFile }: PDFPreviewProps) => {
    const [expanded, setExpanded] = useState(true);

    if (!file) return null;

    const fileURL = URL.createObjectURL(file);

    return (
        <div className="mt-4 bg-white p-4 rounded shadow space-y-2">
            <div className="flex justify-between items-center">
                <h3 className="font-semibold">PDF Preview</h3>
                <div className="space-x-2">
                    <button
                        onClick={() => setExpanded((prev) => !prev)}
                        className="text-sm text-blue-600 hover:underline"
                    >
                        {expanded ? "Collapse" : "Expand"}
                    </button>
                    <button
                        onClick={onRemoveFile}
                        className="text-sm text-red-600 hover:underline"
                    >
                        Remove
                    </button>
                </div>
            </div>

            {expanded && (
                <div className="border rounded overflow-hidden">
                    <iframe
                        src={fileURL}
                        className="w-full h-64"
                        title="PDF Preview"
                    ></iframe>
                </div>
            )}
        </div>
    );
};

export default PDFPreview;
