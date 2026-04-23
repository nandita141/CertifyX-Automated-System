import React from "react";
import ReactDOM from "react-dom/client";
import CertificateDashboard from "./CertificateDashboard";
import StudentForm from "./StudentForm";

function App() {
  return (
    <>
      <CertificateDashboard />
      <StudentForm />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
