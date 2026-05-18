function formatDate(isoString) {
  if (!isoString) return 'Unknown';
  const date = new Date(isoString);
  return date.toLocaleString('en-IN');
}

async function refreshStats() {
  try {
    const res = await fetch("/api/dashboard/stats");
    const stats = await res.json();
    document.getElementById("total-students").textContent = stats.total_students;
    document.getElementById("complete-data").textContent = stats.students_complete;
    document.getElementById("generated").textContent = stats.certificates_generated;
    document.getElementById("downloaded").textContent = stats.certificates_downloaded;
    document.getElementById("emailed").textContent = stats.emails_sent || 0;
  } catch (err) {
    console.error("Error refreshing stats:", err);
  }
}

async function refreshFolders() {
  try {
    const res = await fetch("/api/dashboard/files");
    if (!res.ok) throw new Error("API error");
    const data = await res.json();

    // Email Drafts Folder removed as per user request
  } catch (err) {
    console.error("Error loading files:", err);
  }
}

function openFile(url) { window.open(url, '_blank'); }
function downloadFile(url) { window.location.href = url; }

async function openFolder(folderType) {
  try {
    showMessage("Opening folder...", "info");
    const res = await fetch(`/api/dashboard/open-folder/${folderType}`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      showMessage("Folder opened!", "success");
    } else {
      showMessage(`${data.error}`, "error");
    }
  } catch (err) {
    showMessage(` Error: ${err.message}`, "error");
  }
}

// Global flag to track generation status
let isGenerating = false;

async function refreshActivityLog() {
  try {
    const res = await fetch("/api/dashboard/activity-log");
    const activities = await res.json();

    if (activities.length === 0) {
      document.getElementById("activity-log").innerHTML = '<div style="text-align: center; padding: 30px; color: #999;">No activity yet</div>';
      return;
    }

    // Check if generation is complete based on log
    if (isGenerating) {
      // Check the latest activity (which is at the end of the array from API)
      const newest = activities[activities.length - 1];

      if (newest && (newest.type === 'batch_conversion_complete' || newest.type === 'batch_conversion_failed' || newest.type === 'batch_email_complete')) {
        isGenerating = false;
        const btn = document.getElementById("gen-btn");
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = 'Generate All';
        }

        const specBtn = document.getElementById("gen-spec-btn");
        if (specBtn) {
          specBtn.disabled = false;
          specBtn.innerHTML = 'Specific';
        }

        const emailGenBtn = document.getElementById("gen-email-btn");
        if (emailGenBtn) {
          emailGenBtn.disabled = false;
          emailGenBtn.innerHTML = 'Gen & Send';
        }

        const emailBtn = document.getElementById("email-btn");
        if (emailBtn) {
          emailBtn.disabled = false;
          emailBtn.innerHTML = 'Bulk Send (All)'; // Updated for clarity
        }

        if (newest.type === 'batch_conversion_complete' || newest.type === 'batch_email_complete') {
          showMessage("Process completed successfully!", "success");
        } else {
          showMessage("Process failed. Check logs.", "error");
        }
        refreshStats();
        refreshFolders();
      } else {
        // Even if generation is still happening, refresh stats to show progress
        refreshStats();
        refreshFolders();
      }
    }

    const html = activities.slice().reverse().map(a => {
      const time = new Date(a.timestamp).toLocaleTimeString();
      let className = '', label = a.type;

      // Format activity message
      if (a.type === 'docx_generated') {
        label = `Generated DOCX for Application ID: <strong>${a.data.student_id}</strong>`;
      } else if (a.type === 'conversion_started') {
        label = `Starting PDF Conversion for <strong>${a.data.count}</strong> files...`;
        className = 'activity-info';
      } else if (a.type === 'batch_conversion_complete') {
        className = 'activity-success';
        label = `Batch PDF Conversion Complete! (<strong>${a.data.count}</strong> files)`;
      } else if (a.type === 'batch_conversion_failed') {
        className = 'activity-error';
        label = `Batch Conversion Failed: ${a.data.error || 'Unknown Error'}`;
      } else if (a.type === 'generation_started') {
        label = 'Batch Generation Started';
      } else if (a.type === 'email_sent') {
        label = `Email sent to: <strong>${a.data.student_id}</strong> (${a.data.student_name})`;
        className = 'activity-success';
      } else if (a.type === 'batch_email_complete') {
        label = `<strong>Batch Emailing Complete!</strong> (${a.data.success} sent, ${a.data.failed} failed)`;
        className = a.data.failed > 0 ? 'activity-warning' : 'activity-info';
      } else if (a.type === 'email_failed') {
        label = `Email FAILED for: <strong>${a.data.student_id}</strong> - ${a.data.error}`;
        className = 'activity-error';
      } else if (a.type === 'email_skipped') {
        label = `Email SKIPPED for: <strong>${a.data.student_id}</strong> - ${a.data.reason}`;
        className = 'activity-warning';
      } else if (a.type === 'batch_email_started') {
        label = `Starting Email process for <strong>${a.data.count}</strong> students...`;
        className = 'activity-info';
      } else if (a.data && a.data.student_id) {
        // Fallback for old log types if any
        label = `${a.type}: ${a.data.student_id}`;
      }

      return `<div class="activity-item ${className}"><div class="activity-timestamp">${time}</div><div class="activity-text">${label}</div></div>`;
    }).join('');
    document.getElementById("activity-log").innerHTML = html;
  } catch (err) {
    console.error("Error loading activity:", err);
  }
}

function showMessage(message, type) {
  const msg = document.getElementById("message");
  if (!msg) return;

  msg.textContent = message;
  msg.className = `message ${type}`;
  msg.style.display = "flex";

  // Clear existing timeout
  if (window.msgTimeout) clearTimeout(window.msgTimeout);

  window.msgTimeout = setTimeout(() => {
    msg.style.opacity = "0";
    setTimeout(() => {
      msg.className = "message";
      msg.style.display = "none";
      msg.style.opacity = "1";
    }, 400);
  }, 4000);
}

async function generateAllCertificates() {
  const btn = document.getElementById("gen-btn");
  if (isGenerating) return;

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Generating...';
  showMessage("Started background generation. Watch the log below!", "info");
  isGenerating = true;

  try {
    const res = await fetch("/api/dashboard/generate-all", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      // Success means it started. Polling handles the rest.
    } else {
      showMessage(data.error || "Generation error", "error");
      isGenerating = false;
      btn.disabled = false;
      btn.innerHTML = 'Generate All Certificates';
    }
  } catch (err) {
    showMessage(err.message, "error");
    isGenerating = false;
    btn.disabled = false;
    btn.innerHTML = 'Generate All Certificates';
  }
}

async function generateSpecificCertificate() {
  const specificIdInput = document.getElementById("specific-id-input");
  const studentId = specificIdInput.value.trim();

  if (!studentId) {
    showMessage("Please enter an Application ID", "error");
    return;
  }

  if (isGenerating) return;

  const btn = document.getElementById("gen-spec-btn");
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Generating...';
  showMessage(`Started background generation for ${studentId}. Watch the log below!`, "info");
  isGenerating = true;

  try {
    const res = await fetch("/api/dashboard/generate-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId })
    });
    const data = await res.json();
    if (res.ok) {
      specificIdInput.value = "";
    } else {
      showMessage(data.error || "Generation error", "error");
      isGenerating = false;
      btn.disabled = false;
      btn.innerHTML = 'Generate Specific';
    }
  } catch (err) {
    showMessage(err.message, "error");
    isGenerating = false;
    btn.disabled = false;
    btn.innerHTML = 'Generate Specific';
  }
}

async function downloadAllCertificates() {
  try {
    showMessage("Creating ZIP file...", "info");
    const res = await fetch("/api/dashboard/download-all", { method: "POST" });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "all_certificates.zip";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showMessage("ZIP file downloaded!", "success");
      setTimeout(() => refreshFolders(), 1000);
    } else {
      showMessage("No certificates to download", "error");
    }
  } catch (err) {
    showMessage(err.message, "error");
  }
}

async function downloadSpecificCertificate() {
  const input = document.getElementById("download-specific-id-input");
  const studentId = input.value.trim();

  if (!studentId) {
    showMessage("Please enter an Application ID", "error");
    return;
  }

  try {
    showMessage(`Downloading certificate for ${studentId}...`, "info");
    const res = await fetch(`/api/dashboard/download/${studentId}`);
    
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${studentId}_certificate.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showMessage("Certificate downloaded!", "success");
      input.value = "";
      refreshStats();
      setTimeout(() => refreshFolders(), 1000);
    } else {
      const data = await res.json();
      showMessage(data.error || "File not found", "error");
    }
  } catch (err) {
    showMessage(err.message, "error");
  }
}


async function emailCertificate(filename) {
  if (!confirm(`Are you sure you want to send ${filename} to the student?`)) return;

  showMessage(`Sending email for ${filename}...`, "info");

  // Simulate API call for now (can be connected to backend later)
  setTimeout(() => {
    showMessage(`✅ Email sent successfully for ${filename}!`, "success");
  }, 1500);
}

async function deleteCertificate(filename, type) {
  if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

  try {
    const res = await fetch("/api/dashboard/delete-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: filename, file_type: type })
    });
    const data = await res.json();

    if (res.ok) {
      showMessage(data.message, "success");
      // Refresh the specific list
      if (type === 'generated') refreshGeneratedFiles();
      else if (type === 'downloaded') refreshDownloadedFiles();
      else refreshFolders();

      refreshStats();
    } else {
      showMessage(data.error, "error");
    }
  } catch (err) {
    showMessage(err.message, "error");
  }
}

async function emailAllCertificates() {
  if (!confirm("⚠️ This will generate and send certificates to ALL eligible students. Continue?")) return;

  if (isGenerating) return;
  
  const btn = document.getElementById("email-btn");
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Bulk Sending...';
  showMessage("Started bulk generation and emailing process. Watch the log!", "info");
  isGenerating = true;

  try {
    const res = await fetch("/api/dashboard/generate-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}) // Empty body = ALL students
    });
    
    if (!res.ok) {
      const data = await res.json();
      showMessage(data.error || "Bulk process error", "error");
      isGenerating = false;
      btn.disabled = false;
      btn.innerHTML = 'Bulk Send (All)'; // Match HTML
    }
  } catch (err) {
    showMessage(err.message, "error");
    isGenerating = false;
    btn.disabled = false;
    btn.innerHTML = 'Email All';
  }
}

async function emailSpecificCertificates() {
  const input = document.getElementById("email-specific-id-input");
  const studentIds = input.value.trim();

  if (!studentIds) {
    showMessage("Please enter Application ID(s)", "error");
    return;
  }

  if (isGenerating) return;

  if (!confirm(`Send emails to ${studentIds}? (Only works for generated PDFs)`)) return;

  const btn = document.getElementById("email-spec-btn");
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Sending...';
  showMessage(`Starting Email process for ${studentIds}...`, "info");
  isGenerating = true;

  try {
    const res = await fetch("/api/dashboard/send-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_ids: studentIds })
    });
    
    if (res.ok) {
      input.value = "";
    } else {
      const data = await res.json();
      showMessage(data.error || "Emailing error", "error");
      isGenerating = false;
      btn.disabled = false;
      btn.innerHTML = 'Email Only';
    }
  } catch (err) {
    showMessage(err.message, "error");
    isGenerating = false;
    btn.disabled = false;
    btn.innerHTML = 'Email Only';
  }
}

async function generateAndEmailSpecific() {
  const input = document.getElementById("email-specific-id-input");
  const studentIds = input.value.trim();

  if (!studentIds) {
    showMessage("Please enter Application ID(s)", "error");
    return;
  }

  if (isGenerating) return;

  const btn = document.getElementById("gen-email-btn");
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Processing...';
  showMessage(`Starting Generation & Emailing for ${studentIds}...`, "info");
  isGenerating = true;

  try {
    const res = await fetch("/api/dashboard/generate-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_ids: studentIds })
    });
    
    if (res.ok) {
      input.value = "";
    } else {
      const data = await res.json();
      showMessage(data.error || "Processing error", "error");
      isGenerating = false;
      btn.disabled = false;
      btn.innerHTML = 'Gen & Send';
    }
  } catch (err) {
    showMessage(err.message, "error");
    isGenerating = false;
    btn.disabled = false;
    btn.innerHTML = 'Gen & Send';
  }
}

function openGeneratedModal() {
  document.getElementById("generatedModal").classList.add("active");
  refreshGeneratedFiles();
}

function closeGeneratedModal() {
  document.getElementById("generatedModal").classList.remove("active");
}

function openIndividualModal() {
  document.getElementById("individualModal").classList.add("active");
  refreshIndividualFiles();
}

function closeIndividualModal() {
  document.getElementById("individualModal").classList.remove("active");
}

function openDownloadedModal() {
  document.getElementById("downloadedModal").classList.add("active");
  refreshDownloadedFiles();
}

function closeDownloadedModal() {
  document.getElementById("downloadedModal").classList.remove("active");
}

async function refreshGeneratedFiles() {
  try {
    const res = await fetch("/api/dashboard/files");
    if (!res.ok) throw new Error("API error");
    const data = await res.json();

    if (!data.generated || data.generated.length === 0) {
      document.getElementById("generated-folder").innerHTML = '<div class="empty-state"><div class="empty-icon"></div><div>No certificates generated yet</div></div>';
    } else {
      document.getElementById("generated-folder").innerHTML = data.generated.map(f => `
        <div class="file-card">
          <div class="file-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="file-name" title="${f.display_name}">${f.display_name}</div>
          <div class="file-date">${formatDate(f.generated_at)}</div>
          <div class="file-actions">
            <button class="btn-icon btn-view-file" title="View" onclick="openFile('${f.url}')">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
            <button class="btn-icon btn-download-file" title="Download" onclick="downloadFile('${f.download_url}')">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
            <button class="btn-icon btn-delete-file" title="Delete" onclick="deleteCertificate('${f.name}', 'generated')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error("Error loading generated files:", err);
  }
}

async function refreshIndividualFiles() {
  try {
    const res = await fetch("/api/dashboard/files");
    if (!res.ok) throw new Error("API error");
    const data = await res.json();

    if (!data.individual || data.individual.length === 0) {
      document.getElementById("individual-folder").innerHTML = '<div class="empty-state"><div class="empty-icon"></div><div>No specific certificates generated yet</div></div>';
    } else {
      document.getElementById("individual-folder").innerHTML = data.individual.map(f => `
        <div class="file-card">
          <div class="file-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="file-name" title="${f.display_name}">${f.display_name}</div>
          <div class="file-date">${formatDate(f.generated_at)}</div>
          <div class="file-actions">
            <button class="btn-icon btn-view-file" title="View" onclick="openFile('${f.url}')">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
            <button class="btn-icon btn-download-file" title="Download" onclick="downloadFile('${f.download_url}')">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
            <button class="btn-icon btn-delete-file" title="Delete" onclick="deleteCertificate('${f.name}', 'generated')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error("Error loading specific files:", err);
  }
}

async function refreshDownloadedFiles() {
  try {
    const res = await fetch("/api/dashboard/files");
    if (!res.ok) throw new Error("API error");
    const data = await res.json();

    if (!data.downloaded || data.downloaded.length === 0) {
      document.getElementById("downloaded-folder").innerHTML = '<div class="empty-state"><div class="empty-icon"></div><div>No downloads yet</div></div>';
    } else {
      document.getElementById("downloaded-folder").innerHTML = data.downloaded.map(f => `
        <div class="file-card">
          <div class="file-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          </div>
          <div class="file-name" title="${f.name}">${f.name}</div>
          <div class="file-date">${formatDate(f.created_at)}</div>
          <div class="file-actions">
            <button class="btn-icon btn-download-file" title="Download" onclick="downloadFile('${f.url}')">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
            <button class="btn-icon btn-delete-file" title="Delete" onclick="deleteCertificate('${f.name}', 'downloaded')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error("Error loading downloaded files:", err);
  }
}

// Auto-refresh stats occasionally
setInterval(refreshStats, 5000); // 5 seconds for real-time feel
setInterval(refreshActivityLog, 3000); // 3 seconds for logs

// Initial Load
refreshStats();
refreshFolders();
refreshActivityLog();
