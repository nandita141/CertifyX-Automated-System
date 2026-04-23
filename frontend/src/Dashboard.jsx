import React, { useEffect, useState } from "react";
import CONFIG from "./config";

const API = CONFIG.API_BASE_URL;

export default function Dashboard() {
  const [stats, setStats] = useState({
    total: 0,
    downloaded: 0,
    emails: 0,
  });

  const [students, setStudents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  // ---------------- LOAD DATA ----------------
  const loadDashboard = async () => {
    try {
      const statsRes = await fetch(`${API}/stats`);
      const statsData = await statsRes.json();

      const studentsRes = await fetch(`${API}/students`);
      const studentsData = await studentsRes.json();

      setStats(statsData);
      setStudents(studentsData);
    } catch {
      addLog("❌ Failed to load dashboard data");
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  // ---------------- LOG HELPER ----------------
  const addLog = (msg) => {
    setLogs((prev) => [...prev, msg]);
  };

  // ---------------- GENERATE ----------------
  const generateCertificates = async () => {
    setLoading(true);
    addLog("⚡ Generating certificates...");

    try {
      const res = await fetch(`${API}/generate`, {
        method: "POST",
      });

      const data = await res.json();
      addLog(`✅ ${data.message}`);

      loadDashboard();
    } catch {
      addLog("❌ Generation failed");
    }

    setLoading(false);
  };

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>🎓 Certificate Dashboard</h1>

      {/* ACTION BUTTONS */}
      <div style={styles.card}>
        <h2>Quick Actions</h2>

        <div style={styles.buttonRow}>
          <button
            style={{ ...styles.btn, background: "#4f46e5" }}
            onClick={generateCertificates}
            disabled={loading}
          >
            Generate Certificates
          </button>

          <button style={{ ...styles.btn, background: "#16a34a" }}>
            Download All
          </button>

          <button style={{ ...styles.btn, background: "#ea580c" }}>
            Send Emails
          </button>
        </div>
      </div>

      {/* STATS */}
      <div style={styles.grid}>
        <StatCard title="Total Certificates" value={stats.total} />
        <StatCard title="Downloaded" value={stats.downloaded} />
        <StatCard title="Emails Sent" value={stats.emails} />
      </div>

      {/* STUDENTS */}
      <div style={styles.card}>
        <h2>Students ({students.length})</h2>

        <div style={styles.scroll}>
          {students.map((s, i) => (
            <p key={i}>
              {s.student_id} — {s.student_name}
            </p>
          ))}
        </div>
      </div>

      {/* LOG */}
      <div style={styles.card}>
        <h2>Activity Log</h2>

        <div style={styles.scroll}>
          {logs.length === 0
            ? "Waiting for activity..."
            : logs.map((l, i) => <p key={i}>{l}</p>)}
        </div>
      </div>
    </div>
  );
}

// ---------------- STAT CARD ----------------
function StatCard({ title, value }) {
  return (
    <div style={styles.statCard}>
      <p>{title}</p>
      <h2>{value || 0}</h2>
    </div>
  );
}

// ---------------- STYLES ----------------
const styles = {
  page: {
    padding: "30px",
    background: "#f1f5f9",
    minHeight: "100vh",
    fontFamily: "Arial",
  },

  title: {
    marginBottom: "20px",
  },

  card: {
    background: "white",
    padding: "20px",
    borderRadius: "10px",
    marginBottom: "20px",
    boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
  },

  buttonRow: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
  },

  btn: {
    padding: "12px 18px",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
  },

  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "15px",
    marginBottom: "20px",
  },

  statCard: {
    background: "white",
    padding: "20px",
    borderRadius: "10px",
    boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
  },

  scroll: {
    maxHeight: "150px",
    overflowY: "auto",
  },
};
