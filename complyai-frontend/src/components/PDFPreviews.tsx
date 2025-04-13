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
        <div className="mt-4 bg-white dark:bg-gray-900 text-gray-500 dark:text-white p-4 rounded-lg shadow space-y-2 text-xs sm:text-sm">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center space-y-2 sm:space-y-0">
                <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2">
                    <div className="flex items-center space-x-2">
                        <FiCheckCircle className="text-green-500" />
                        <h3 className="font-semibold">Uploaded PDF Preview</h3>
                    </div>
                    <span className="text-[10px] text-gray-500 dark:text-gray-400 mt-1 sm:mt-0">
                        name: {file.name} | size: {(file.size / 1024 / 1024).toFixed(2)} MB | Type: {file.type}
                    </span>
                </div>
                <div className="flex items-center space-x-2 ">
                    <button
                        onClick={() => setExpanded((prev) => !prev)}
                        className="text-blue-600 hover:underline flex items-center space-x-1 text-xs"
                    >
                        {expanded ? <><FiChevronUp /><span>Collapse</span></> : <><FiChevronDown /><span>Expand</span></>}
                    </button>
                    <button
                        onClick={onRemoveFile}
                        className="text-red-600 hover:underline flex items-center space-x-1 text-xs"
                    >
                        <FiTrash2 />
                        <span>Remove</span>
                    </button>
                </div>
            </div>

            {expanded && (
                <div className="border rounded overflow-hidden">
                    <iframe
                        src={fileURL}
                        className="w-full h-60 sm:h-72 md:h-96"
                        title="PDF Preview"
                    />
                </div>
            )}
        </div>
    );
};

export default PDFPreview;
