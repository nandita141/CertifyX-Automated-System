import React, { useEffect, useState } from "react";
import "./dashboard.css";

const API = "http://127.0.0.1:5000/api";

export default function CertificateDashboard() {

  const [stats, setStats] = useState({
    pdf: 0,
    downloaded: 0,
    drafts: 0
  });

  const [logs, setLogs] = useState([]);

  // =========================
  // Load folder stats
  // =========================
  const loadStats = async () => {
    try {
      const res = await fetch(`${API}/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setLogs(l => [...l, "❌ Failed to load stats"]);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  // =========================
  // Generate certificates
  // =========================
  const generateCertificates = async () => {

    setLogs(l => [...l, "⚡ Generating certificates..."]);

    try {
      await fetch(`${API}/generate`, { method: "POST" });

      setLogs(l => [...l, " Certificates generated successfully"]);
      loadStats();

    } catch {
      setLogs(l => [...l, "❌ Generation failed"]);
    }
  };

  // =========================
  // Download (folder open hint)
  // =========================
  const downloadCertificates = () => {
    setLogs(l => [...l, "📂 Open pdf_storage folder to access certificates"]);
  };

  return (
    <div className="dashboard">

      <h1>🎓 Automatic Certificate Dashboard</h1>

      {/* Buttons */}
      <div className="actions">

        <button
          className="btn purple"
          onClick={generateCertificates}
        >
          Generate Certificates
        </button>

        <button
          className="btn green"
          onClick={downloadCertificates}
        >
          View PDFs
        </button>

        <button className="btn orange">
          Send Email
        </button>

      </div>

      {/* Folder cards */}
      <div className="folders">

        <FolderCard title="PDF Folder" value={stats.pdf} />
        <FolderCard title="Downloaded" value={stats.downloaded} />
        <FolderCard title="Drafts" value={stats.drafts} />

      </div>

      {/* Activity log */}
      <div className="logs">

        <h2>Activity Log</h2>

        {logs.length === 0 ? (
          <p>No activity yet...</p>
        ) : (
          logs.map((log, i) => (
            <p key={i}>{log}</p>
          ))
        )}

      </div>

    </div>
  );
}

// =========================
// Folder card component
// =========================
function FolderCard({ title, value }) {

  return (
    <div className="folder">

      <h3>{title}</h3>
      <p>{value}</p>

    </div>
  );
}
