import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import UploadForm from "./components/UploadForm";
import './App.css'


function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <UploadForm />
    </div>
  );
}

export default App;