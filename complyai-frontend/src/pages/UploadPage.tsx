// src/pages/UploadPage.tsx

import { useState } from "react";
import UploadForm from "../components/UploadForm";
import PDFPreview from "../components/PDFPreviews";

const UploadPage = () => {
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="bg-gray-100 dark:bg-gray-800 py-10 px-4 text-gray-800 dark:text-white">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Page Heading */}
        <div className="text-center space-y-2">
          <h1 className="text-xl sm:text-2xl font-semibold">
            📤 Generate Compliance Report
          </h1>
        </div>

        {/* Upload Form */}
        <UploadForm setFile={setFile} file={file} />

        {/* PDF Preview */}
        <PDFPreview file={file} onRemoveFile={() => setFile(null)} />
      </div>
    </div>
  );
};

export default UploadPage;
