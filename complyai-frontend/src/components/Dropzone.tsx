// src/components/Dropzone.tsx

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface DropzoneProps {
    onFileAccepted: (file: File) => void;
    file: File | null;
    onRemoveFile: () => void;
}

const Dropzone = ({ onFileAccepted, file, onRemoveFile }: DropzoneProps) => {
    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            onFileAccepted(acceptedFiles[0]);
        }
    }, [onFileAccepted]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': [] }
    });

    return (
        <div>
            {!file ? (
                <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded p-6 text-center cursor-pointer transition ${
                        isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"
                    } hover:border-blue-400`}
                >
                    <input {...getInputProps()} />
                    <p className="text-sm">
                        {isDragActive ? "Drop the PDF file here..." : "Drag & drop a PDF here, or click to select"}
                    </p>
                </div>
            ) : (
                <div className="border rounded p-4 bg-gray-100 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                        <span className="text-2xl">📄</span>
                        <div>
                            <p className="text-sm font-medium text-gray-900">{file.name}</p>
                            <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onRemoveFile}
                        className="text-red-500 text-sm hover:underline"
                    >
                        Remove
                    </button>
                </div>
            )}
        </div>
    );
};

export default Dropzone;
