// src/pages/UploadPage.tsx

import UploadForm from "../components/UploadForm";

const UploadPage = () => {
    return (
        <div>
            <h2 className="text-2xl font-semibold mb-4">Upload Policy</h2>
            <UploadForm />
        </div>
    );
};

export default UploadPage;