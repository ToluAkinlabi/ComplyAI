// src/pages/UploadPage.tsx

import { useState } from "react";
import UploadForm from "../components/UploadForm";
import PDFPreview from "../components/PDFPreviews";

const UploadPage = () => {
    const [file, setFile] = useState<File | null>(null);
  
    return (
      <div className="h-screen bg-gray-100 py-10 px-4 ">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Page Heading */}
          <div className="text-center space-y-1">
            <h1 className="text-3xl font-semibold text-gray-800">📤 Generate Compliance Report</h1>
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
