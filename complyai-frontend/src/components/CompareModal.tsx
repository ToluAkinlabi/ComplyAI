// src/components/CompareModal.tsx

import { useEffect, useState } from "react";
import Select from "react-select";
import ReportComparison from "../dashboard/ReportComparison";
import toast from "react-hot-toast";
import "./CompareModal.css"; 

interface CompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportNames: string[];
}

const CompareModal = ({ isOpen, onClose, reportNames }: CompareModalProps) => {
  const [selectedOptions, setSelectedOptions] = useState<any[]>([]);

  /* Toast messages are commented out to avoid cluttering the UI with notifications.
  useEffect(() => {
    if (isOpen) toast.success("Opened Compare Reports");
    else if (!isOpen && selectedOptions.length) toast("Comparison closed");

    if (!isOpen) setSelectedOptions([]);
  }, [isOpen]); */

  const options = reportNames.map((name) => ({ value: name, label: name }));

  if (!isOpen) return null;

  return (
    <div className="compare-modal-overlay">
      <div className="compare-modal">
        <button
          onClick={onClose}
          className="absolute top-3 right-4 text-gray-500 hover:text-black text-lg"
        >
          &times;
        </button>
        <h2 className="text-xl font-semibold mb-4">Compare Reports</h2>

        <Select
          isMulti
          options={options}
          value={selectedOptions}
          onChange={setSelectedOptions}
          className="mb-4"
        />

        {selectedOptions.length > 0 && (
          <ReportComparison reports={selectedOptions.map((o) => o.value)} />
        )}
      </div>
    </div>
  );
};

export default CompareModal;
