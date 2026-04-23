let validID = false;
let currentStudentId = "";

// ===== LOAD SUPERVISORS =====
async function loadSupervisors() {
    try {
        const res = await fetch("/supervisors");           
        const data = await res.json();

        const list = Array.isArray(data) ? data : (data.supervisors || []);
        const dropdown = document.getElementById("supervisor");

        // Clear existing options except the first one
        while (dropdown.options.length > 1) {
            dropdown.remove(1);
        }

        list.sort().forEach(name => {
            const opt = document.createElement("option");
            opt.value = name;
            opt.text = name;
            dropdown.appendChild(opt);
        });

        console.log("Loaded", list.length, "supervisors");
    } catch (err) {
        console.error("Supervisor load error:", err);
        showStatus("Error loading supervisors", "error");
    }
}

// ===== SHOW STATUS MESSAGE =====
function showStatus(message, type) {
    const statusDiv = document.getElementById("status");
    statusDiv.textContent = message;
    statusDiv.className = "status-message " + type;
}

// ===== CHECK ID & LOAD STUDENT DATA =====
async function checkID() {
    const id = document.getElementById("application_id").value.trim();

    if (!id) {
        showStatus("Enter Application ID", "error");
        return;
    }

    const verifyBtn = document.querySelector('.btn-verify');
    const originalText = verifyBtn.textContent;
    verifyBtn.textContent = 'Verifying...';
    verifyBtn.disabled = true;

    try {
        const res = await fetch(`/check-id/${id}`);
        const data = await res.json();

        console.log("Backend response:", data);

        validID = data.valid === true; // Explicitly check for true
        currentStudentId = id;

        if (validID) {
            showStatus("Valid Application ID - Loading your data...", "success");
            document.getElementById("form-fields").classList.remove("hidden");

            // Smooth scroll to form fields
            setTimeout(() => {
                document.getElementById("form-fields").scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);

            // Auto-populate student data from master dataset
            const studentData = data.student_data || {};
            console.log("Student data:", studentData);

            // Fill student name
            const nameField = document.getElementById("student_name");
            if (nameField && studentData.student_name) {
                nameField.value = studentData.student_name;
                nameField.readOnly = true;
                nameField.style.background = "#f1f5f9";
                nameField.style.cursor = "not-allowed";
            }

            // Fill existing form data
            if (studentData.supervisor_name) {
                document.getElementById("supervisor").value = studentData.supervisor_name;
            }
            if (studentData.internship_start_date) {
                document.getElementById("start_date").value = studentData.internship_start_date;
            }
            if (studentData.internship_end_date) {
                document.getElementById("end_date").value = studentData.internship_end_date;
            }
            if (studentData.no_of_weeks) {
                document.getElementById("weeks").value = studentData.no_of_weeks;
            }
            if (studentData.focused_on) {
                document.getElementById("focused_on").value = studentData.focused_on;
            }
            if (studentData.contributed_towards) {
                document.getElementById("contributed_towards").value = studentData.contributed_towards;
            }

            // Recalculate weeks if dates are filled
            calcWeeks();

            console.log("Student data loaded successfully");
        } else {
            showStatus("Invalid Application ID", "error");
            document.getElementById("form-fields").classList.add("hidden");
            validID = false;
        }

    } catch (err) {
        console.error("ID check error:", err);
        showStatus("Error checking ID: " + err.message, "error");
        validID = false;
    } finally {
        verifyBtn.textContent = originalText;
        verifyBtn.disabled = false;
    }
}

// ===== CALCULATE WEEKS =====
function calcWeeks() {
    const startVal = document.getElementById("start_date").value;
    const endVal = document.getElementById("end_date").value;

    if (!startVal || !endVal) return;

    const start = new Date(startVal);
    const end = new Date(endVal);

    if (end < start) {
        document.getElementById("weeks").value = "";
        alert("End date must be after start date");
        return;
    }

    const diffTime = end - start;
    const diffDays = diffTime / (1000 * 60 * 60 * 24);
    const weeks = Math.ceil(diffDays / 7);

    document.getElementById("weeks").value = weeks;
}

// ===== SUBMIT FORM & GENERATE CERTIFICATE (Single Step) =====
async function submitForm() {
    console.log("🔵 submitForm() called");

    const btn = document.getElementById("final-submit-btn");

    if (!validID) {
        showStatus("Please verify your Application ID first", "error");
        return;
    }

    const supervisor = document.getElementById("supervisor").value;
    if (!supervisor) {
        showStatus("Please select a Supervisor", "error");
        return;
    }

    const startDate = document.getElementById("start_date").value;
    const endDate = document.getElementById("end_date").value;
    const focusedOn = document.getElementById("focused_on").value.trim();
    const contributedTowards = document.getElementById("contributed_towards").value.trim();

    if (!startDate || !endDate) {
        showStatus("Please select both start and end dates", "error");
        return;
    }

    if (!focusedOn) {
        showStatus("Please fill in what you focused on during the internship", "error");
        return;
    }

    if (!contributedTowards) {
        showStatus("Please fill in what you contributed towards", "error");
        return;
    }

    // Disable button and show saving state
    btn.textContent = "Saving...";
    btn.disabled = true;

    const payload = {
        student_id: currentStudentId,
        supervisor_name: supervisor,
        internship_start_date: startDate,
        internship_end_date: endDate,
        no_of_weeks: document.getElementById("weeks").value,
        focused_on: focusedOn,
        contributed_towards: contributedTowards
    };

    try {
        // Step 1: Save form data
        const res = await fetch("/submit-form", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (!res.ok) {
            showStatus(data.error || "Error submitting form", "error");
            btn.textContent = "FINAL SUBMIT";
            btn.disabled = false;
            return;
        }

        // Step 2: Generate certificate immediately
        showStatus("Details saved! Generating certificate...", "success");
        btn.textContent = "Generating...";

        const certRes = await fetch("/generate-certificate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: currentStudentId })
        });

        const certData = await certRes.json();

        if (certRes.ok) {
            showStatus("SUBMITTED SUCCESSFULLY!", "success");
            btn.textContent = "Submitted Successfully ✓";
            btn.style.background = "#059669";

            // Revert original UI, hide the form body
            document.getElementById("form-fields").style.display = "none";

            // Completely hide the application ID form group instead of replacing its HTML
            document.querySelector('.form-group:first-of-type').style.display = "none";
        } else {
            showStatus("Error: " + (certData.error || "Unknown error"), "error");
            btn.textContent = "FINAL SUBMIT";
            btn.disabled = false;
        }

    } catch (err) {
        showStatus("Error: " + err.message, "error");
        btn.textContent = "FINAL SUBMIT";
        btn.disabled = false;
    }
}

// ===== PAGE LOAD =====
window.onload = function () {
    loadSupervisors();

    // Allow Enter key to check ID
    const appIdInput = document.getElementById("application_id");
    if (appIdInput) {
        appIdInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") checkID();
        });
    }
};
