// src/components/PDFPreview.tsx

import { useState } from "react";
import { FiCheckCircle, FiTrash2, FiChevronDown, FiChevronUp } from "react-icons/fi";

interface PDFPreviewProps {
    file: File | null;
    onRemoveFile: () => void;
}

const PDFPreview = ({ file, onRemoveFile }: PDFPreviewProps) => {
    const [expanded, setExpanded] = useState(true);

    if (!file) return null;

    const fileURL = URL.createObjectURL(file);

    return (
        <div className="mt-4 bg-white p-4 rounded-lg shadow space-y-2 transition duration-300 ease-in-out">
            <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                    <FiCheckCircle className="text-green-500" />
                    <h3 className="font-semibold text-sm">Uploaded PDF Preview</h3>
                    <span className="text-xs text-gray-500 mt-1">name: {file.name} | size: {(file.size / 1024 / 1024).toFixed(2)} MB | Type: {file.type}</span>
                </div>
                <div className="space-x-3 flex items-center">
                    <button
                        onClick={() => setExpanded((prev) => !prev)}
                        className="text-sm text-blue-600 hover:underline flex items-center space-x-1"
                    >
                        {expanded ? <><FiChevronUp /> <span>Collapse</span></> : <><FiChevronDown /> <span>Expand</span></>}
                    </button>
                    <button
                        onClick={onRemoveFile}
                        className="text-sm text-red-600 hover:underline flex items-center space-x-1"
                    >
                        <FiTrash2 />
                        <span>Remove</span>
                    </button>
                </div>
            </div>

            {expanded && (
                <div className="border rounded overflow-hidden transition-all">
                    <iframe
                        src={fileURL}
                        className="w-full h-72"
                        title="PDF Preview"
                    ></iframe>
                </div>
            )}
        </div>
    );
};

export default PDFPreview;
