import React, { useState, useEffect } from "react";

const API = "http://127.0.0.1:8000";

export default function StudentForm() {
  const [form, setForm] = useState({});
  const [supervisors, setSupervisors] = useState([]);

  useEffect(() => {
    fetch(`${API}/supervisors`)
      .then((res) => res.json())
      .then((data) => setSupervisors(data))
      .catch((err) => console.error(err));
  }, []);

  const loadStudent = async () => {
    try {
      const res = await fetch(`${API}/student/${form.student_id}`);
      const data = await res.json();

      if (!data.error) {
        setForm(data);
      } else {
        alert("Student not found");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const update = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const save = async () => {
    try {
      await fetch(`${API}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      alert("Saved!");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ padding: "40px" }}>
      <h2>Internship Form</h2>

      <input
        type="text"
        name="student_id"
        placeholder="Student ID"
        value={form.student_id || ""}
        onChange={update}
      />

      <button onClick={loadStudent}>Load</button>

      <br /><br />

      <input
        type="text"
        name="internship_start_date"
        placeholder="Start Date"
        value={form.internship_start_date || ""}
        onChange={update}
      />

      <input
        type="text"
        name="internship_end_date"
        placeholder="End Date"
        value={form.internship_end_date || ""}
        onChange={update}
      />

      <br /><br />

      <select
        name="supervisor_name"
        value={form.supervisor_name || ""}
        onChange={update}
      >
        <option value="">Select Supervisor</option>
        {supervisors.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <br /><br />

      <textarea
        name="focused_on"
        placeholder="Focused On"
        value={form.focused_on || ""}
        onChange={update}
      />

      <br /><br />

      <textarea
        name="contributed_towards"
        placeholder="Contributed Towards"
        value={form.contributed_towards || ""}
        onChange={update}
      />

      <br /><br />

      <button onClick={save}>Save</button>
    </div>
  );
}
