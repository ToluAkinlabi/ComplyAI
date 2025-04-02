// src/pages/UploadPage.tsx

import { useState } from "react";
import UploadForm from "../components/UploadForm";
import PDFPreview from "../components/PDFPreviews";

const UploadPage = () => {
    const [file, setFile] = useState<File | null>(null);

    return (
        <div className="flex justify-center items-center h-full bg-gray-100 py-8 px-4">
            <div className="w-full max-w-3xl space-y-4">
                <UploadForm setFile={setFile} file={file} />
                <PDFPreview file={file} onRemoveFile={() => setFile(null)} />
            </div>
        </div>
    );
};

export default UploadPage;
