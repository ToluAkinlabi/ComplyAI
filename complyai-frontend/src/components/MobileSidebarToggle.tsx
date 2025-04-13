// src/components/MobileSidebarToggle.tsx
import { FaBars } from "react-icons/fa";

interface Props {
  onToggle: () => void;
}

const MobileSidebarToggle = ({ onToggle }: Props) => {
  return (
    <button
      onClick={onToggle}
      className="md:hidden text-xl text-gray-800 dark:text-white"
    >
      <FaBars />
    </button>
  );
};

export default MobileSidebarToggle;


