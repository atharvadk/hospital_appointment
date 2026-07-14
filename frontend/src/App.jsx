import React, { useState, useEffect, useRef } from "react";

const API_BASE = "http://localhost:8000";

// SVG Icons
const Icons = {
  Clinic: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
  ),
  Calendar: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
  ),
  Clock: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
  ),
  User: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
  ),
  LogOut: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
  ),
  Search: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
  ),
  Plus: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5v14"/></svg>
  ),
  Check: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
  )
};

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [role, setRole] = useState(localStorage.getItem("role") || "");
  const [userName, setUserName] = useState(localStorage.getItem("userName") || "");
  
  const [currentTab, setCurrentTab] = useState("dashboard");
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [takenReminders, setTakenReminders] = useState({});
  const [loadingData, setLoadingData] = useState(false);
  const [alert, setAlert] = useState(null);
  
  // Auth Form states
  const [isLogin, setIsLogin] = useState(true);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authRole, setAuthRole] = useState("patient");
  const [authLoading, setAuthLoading] = useState(false);

  // Patient states
  const [doctorsList, setDoctorsList] = useState([]);
  const [searchSpeciality, setSearchSpeciality] = useState("");
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [activeHold, setActiveHold] = useState(null);
  const [holdTimeRemaining, setHoldTimeRemaining] = useState(0);
  const [symptomsText, setSymptomsText] = useState("");
  const [patientAppointments, setPatientAppointments] = useState([]);
  const [patientReminders, setPatientReminders] = useState([]);
  const [bookingLoading, setBookingLoading] = useState(false);

  // Doctor states
  const [doctorAppointments, setDoctorAppointments] = useState([]);
  const [activeNoteAppt, setActiveNoteAppt] = useState(null);
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [prescription, setPrescription] = useState("");
  const [postVisitLoading, setPostVisitLoading] = useState(false);

  // Admin states
  const [adminDoctors, setAdminDoctors] = useState([]);
  const [editingDoctor, setEditingDoctor] = useState(null);
  const [newDoctorName, setNewDoctorName] = useState("");
  const [newDoctorEmail, setNewDoctorEmail] = useState("");
  const [newDoctorPassword, setNewDoctorPassword] = useState("");
  const [newDoctorSpeciality, setNewDoctorSpeciality] = useState("General Medicine");
  const [adminSelectedDoctorId, setAdminSelectedDoctorId] = useState("");
  const [leaveDateInput, setLeaveDateInput] = useState("");
  const [conflictWarning, setConflictWarning] = useState("");

  const holdTimerRef = useRef(null);

  // Handle URL redirect query params for Google Calendar connection
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const calendarConnected = params.get("calendar_connected");
    const calendarError = params.get("calendar_error");

    if (calendarConnected) {
      showAlert("success", "Google Calendar connected successfully! Events will now sync automatically.");
      setCalendarConnected(true);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (calendarError) {
      showAlert("danger", `Google Calendar Sync Failed: ${calendarError}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Set default tab when role changes
  useEffect(() => {
    if (token) {
      setCurrentTab("dashboard");
      fetchRoleData();
    } else {
      setCurrentTab("auth");
    }
  }, [token, role]);

  // Hold slot countdown timer
  useEffect(() => {
    if (activeHold) {
      const calculateTimeLeft = () => {
        const lockedTime = new Date(activeHold.locked_until.endsWith("Z") ? activeHold.locked_until : activeHold.locked_until + "Z");
        const diff = lockedTime - new Date();
        if (diff <= 0) {
          setActiveHold(null);
          setHoldTimeRemaining(0);
          showAlert("warning", "Your slot hold lock has expired. Please select a slot again.");
          if (selectedDoctor) fetchSlots(selectedDoctor.id, selectedDate);
        } else {
          setHoldTimeRemaining(Math.ceil(diff / 1000));
        }
      };
      
      calculateTimeLeft();
      holdTimerRef.current = setInterval(calculateTimeLeft, 1000);
    } else {
      if (holdTimerRef.current) clearInterval(holdTimerRef.current);
    }

    return () => {
      if (holdTimerRef.current) clearInterval(holdTimerRef.current);
    };
  }, [activeHold]);

  const showAlert = (type, message) => {
    setAlert({ type, message });
    setTimeout(() => setAlert(null), 8000);
  };

  const fetchRoleData = () => {
    if (role === "patient") {
      fetchDoctors();
      fetchPatientAppointments();
      fetchPatientReminders();
      fetchCalendarStatus();
    } else if (role === "doctor") {
      fetchDoctorAppointments();
      fetchCalendarStatus();
    } else if (role === "admin") {
      fetchAdminDoctors();
    }
  };

  // Auth Operations
  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    
    try {
      if (isLogin) {
        const formData = new URLSearchParams();
        formData.append("username", authEmail);
        formData.append("password", authPassword);

        const response = await fetch(`${API_BASE}/api/auth/login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: formData,
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Authentication failed");
        }

        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("userName", data.name);
        setToken(data.access_token);
        setRole(data.role);
        setUserName(data.name);
        showAlert("success", `Welcome back, ${data.name}!`);
      } else {
        const response = await fetch(`${API_BASE}/api/auth/register`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: authEmail,
            password: authPassword,
            full_name: authName,
            role: authRole
          }),
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Registration failed");
        }

        showAlert("success", "Registration successful! Please log in.");
        setIsLogin(true);
      }
    } catch (err) {
      showAlert("danger", err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("userName");
    setToken("");
    setRole("");
    setUserName("");
    setActiveHold(null);
    setCurrentTab("auth");
  };

  // Google Calendar Integration
  const fetchCalendarStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/calendar/status`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCalendarConnected(data.connected);
      }
    } catch (err) {
      console.error("Failed to check calendar status", err);
    }
  };

  const handleGoogleSync = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/calendar/auth?token=${token}`);
      if (!response.ok) throw new Error("Could not initiate Google Auth link");
      const data = await response.json();
      window.location.href = data.authorization_url;
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleGoogleDisconnect = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/calendar/disconnect`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to disconnect calendar");
      showAlert("success", "Google Calendar disconnected successfully.");
      setCalendarConnected(false);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleMarkTaken = (id) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setTakenReminders(prev => ({ ...prev, [id]: timeStr }));
    showAlert("success", "Excellent! You checked off this dose. Keep it up!");
  };

  const SkeletonCard = () => (
    <div className="card">
      <div className="skeleton-title skeleton-line"></div>
      <div className="skeleton-line" style={{ width: "80%" }}></div>
      <div className="skeleton-line" style={{ width: "40%" }}></div>
      <div className="skeleton-line" style={{ width: "60%" }}></div>
    </div>
  );

  // Patient API Calls
  const fetchDoctors = async (spec = "") => {
    setLoadingData(true);
    try {
      const url = spec ? `${API_BASE}/api/patient/doctors?specialisation=${spec}` : `${API_BASE}/api/patient/doctors`;
      const response = await fetch(url, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch doctors list");
      const data = await response.json();
      setDoctorsList(data);
    } catch (err) {
      showAlert("danger", err.message);
    } finally {
      setLoadingData(false);
    }
  };

  const fetchSlots = async (doctorId, date) => {
    try {
      const response = await fetch(`${API_BASE}/api/patient/doctors/${doctorId}/slots?date=${date}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch slots");
      const data = await response.json();
      setAvailableSlots(data);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const fetchPatientAppointments = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/patient/appointments`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch appointments");
      const data = await response.json();
      setPatientAppointments(data);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const fetchPatientReminders = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/patient/reminders`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch medication reminders");
      const data = await response.json();
      setPatientReminders(data);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleHoldSlot = async (slot) => {
    try {
      const response = await fetch(`${API_BASE}/api/patient/slots/hold`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          doctor_id: selectedDoctor.id,
          date: selectedDate,
          start_time: slot.start_time,
          end_time: slot.end_time
        })
      });

      if (response.status === 409) {
        throw new Error("This slot is already booked or held by another user");
      }
      if (!response.ok) throw new Error("Failed to lock slot");

      const data = await response.json();
      setActiveHold(data);
      showAlert("info", `Slot locked! Complete details below within 5 minutes to confirm booking.`);
      fetchSlots(selectedDoctor.id, selectedDate);

      // Smooth scroll to details form and focus symptom input
      setTimeout(() => {
        const formEl = document.getElementById("booking-details-form");
        if (formEl) {
          formEl.scrollIntoView({ behavior: "smooth" });
          const textEl = formEl.querySelector("textarea");
          if (textEl) textEl.focus();
        }
      }, 300);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleBookAppointment = async (e) => {
    e.preventDefault();
    if (!activeHold) return;
    setBookingLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/patient/appointments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          doctor_id: activeHold.doctor_id,
          date: activeHold.date,
          start_time: activeHold.start_time,
          end_time: activeHold.end_time,
          symptoms: symptomsText
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Booking failed");
      }

      showAlert("success", "Appointment booked successfully! Summary generated.");
      setActiveHold(null);
      setSymptomsText("");
      fetchPatientAppointments();
      fetchPatientReminders();
      setSelectedDoctor(null);
    } catch (err) {
      showAlert("danger", err.message);
    } finally {
      setBookingLoading(false);
    }
  };

  // Doctor API Calls
  const fetchDoctorAppointments = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/doctor/appointments`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch appointments");
      const data = await response.json();
      setDoctorAppointments(data);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handlePostVisitNotes = async (e) => {
    e.preventDefault();
    setPostVisitLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/doctor/appointments/${activeNoteAppt.id}/post-visit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          clinical_notes: clinicalNotes,
          prescription: prescription
        })
      });

      if (!response.ok) throw new Error("Failed to submit notes");

      showAlert("success", "Clinical notes submitted and reminders created!");
      setActiveNoteAppt(null);
      setClinicalNotes("");
      setPrescription("");
      fetchDoctorAppointments();
    } catch (err) {
      showAlert("danger", err.message);
    } finally {
      setPostVisitLoading(false);
    }
  };

  // Admin API Calls
  const fetchAdminDoctors = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/doctors`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!response.ok) throw new Error("Failed to fetch doctor profiles");
      const data = await response.json();
      setAdminDoctors(data);
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleAddDoctor = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/admin/doctors`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          email: newDoctorEmail,
          password: newDoctorPassword,
          full_name: newDoctorName,
          role: "doctor"
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to create doctor account");
      }

      showAlert("success", "Doctor profile created successfully.");
      setNewDoctorName("");
      setNewDoctorEmail("");
      setNewDoctorPassword("");
      fetchAdminDoctors();
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleUpdateDoctorConfig = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE}/api/admin/doctors/${editingDoctor.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          specialisation: editingDoctor.specialisation,
          working_hours: editingDoctor.working_hours,
          slot_duration: parseInt(editingDoctor.slot_duration),
          bio: editingDoctor.bio
        })
      });

      if (!response.ok) throw new Error("Failed to update profile configurations");

      showAlert("success", "Doctor configurations updated successfully.");
      setEditingDoctor(null);
      fetchAdminDoctors();
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleAddLeave = async (e) => {
    e.preventDefault();
    if (!adminSelectedDoctorId || !leaveDateInput) return;

    try {
      const response = await fetch(`${API_BASE}/api/admin/doctors/${adminSelectedDoctorId}/leave`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ date: leaveDateInput })
      });

      if (!response.ok) throw new Error("Failed to register doctor leave");

      const data = await response.json();
      showAlert("success", `Leave added successfully! Conflicting appointments cancelled: ${data.cancelled_appointments_count}`);
      setLeaveDateInput("");
      fetchAdminDoctors();
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  const handleRemoveLeave = async (doctorId, date) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/doctors/${doctorId}/leave/${date}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (!response.ok) throw new Error("Failed to remove doctor leave");

      showAlert("success", "Leave date removed successfully.");
      fetchAdminDoctors();
    } catch (err) {
      showAlert("danger", err.message);
    }
  };

  // Formatting helper
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  return (
    <div>
      {/* Navbar */}
      <nav className="navbar">
        <div className="brand">
          <Icons.Clinic />
          <span>Aegis Health Manager</span>
        </div>
        {token && (
          <div className="nav-links">
            <div 
              className={`nav-item ${currentTab === "dashboard" ? "active" : ""}`}
              onClick={() => { setCurrentTab("dashboard"); fetchRoleData(); }}
            >
              Dashboard
            </div>
            
            {role === "patient" && (
              <>
                <div 
                  className={`nav-item ${currentTab === "book" ? "active" : ""}`}
                  onClick={() => { setCurrentTab("book"); fetchDoctors(); }}
                >
                  Book Slot
                </div>
                <div 
                  className={`nav-item ${currentTab === "reminders" ? "active" : ""}`}
                  onClick={() => { setCurrentTab("reminders"); fetchPatientReminders(); }}
                >
                  Reminders
                </div>
              </>
            )}

            {role === "admin" && (
              <>
                <div 
                  className={`nav-item ${currentTab === "add_doctor" ? "active" : ""}`}
                  onClick={() => setCurrentTab("add_doctor")}
                >
                  Register Doctor
                </div>
                <div 
                  className={`nav-item ${currentTab === "leaves" ? "active" : ""}`}
                  onClick={() => { setCurrentTab("leaves"); fetchAdminDoctors(); }}
                >
                  Manage Leaves
                </div>
              </>
            )}
            
            <div className="nav-item" onClick={handleLogout} style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--danger)" }}>
              <Icons.LogOut /> Log Out
            </div>
          </div>
        )}
      </nav>

      {/* Main Container */}
      <div className="dashboard-container">
        {/* Global Alerts */}
        {alert && (
          <div className={`alert alert-${alert.type}`}>
            <div>{alert.message}</div>
          </div>
        )}

        {/* ==================== AUTH TABS ==================== */}
        {!token && (
          <div className="auth-page">
            <div className="auth-card">
              <div className="auth-header">
                <h2>{isLogin ? "Welcome Back" : "Create Account"}</h2>
                <p>{isLogin ? "Sign in to access your clinic portal" : "Register as a patient or staff member"}</p>
              </div>

              <form onSubmit={handleAuth}>
                {!isLogin && (
                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input 
                      type="text" 
                      className="form-input" 
                      value={authName} 
                      onChange={(e) => setAuthName(e.target.value)} 
                      placeholder="Jane Smith"
                      required
                    />
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input 
                    type="email" 
                    className="form-input" 
                    value={authEmail} 
                    onChange={(e) => setAuthEmail(e.target.value)} 
                    placeholder="name@example.com"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input 
                    type="password" 
                    className="form-input" 
                    value={authPassword} 
                    onChange={(e) => setAuthPassword(e.target.value)} 
                    placeholder="••••••••"
                    required
                  />
                </div>

                {!isLogin && (
                  <div className="form-group">
                    <label className="form-label">Portal Access Role</label>
                    <select 
                      className="form-select" 
                      value={authRole} 
                      onChange={(e) => setAuthRole(e.target.value)}
                    >
                      <option value="patient">Patient Portal</option>
                      <option value="doctor">Doctor Portal</option>
                      <option value="admin">System Administrator</option>
                    </select>
                  </div>
                )}

                <button type="submit" className="btn btn-primary btn-block" disabled={authLoading}>
                  {authLoading ? "Processing..." : isLogin ? "Sign In" : "Register"}
                </button>
              </form>

              <div style={{ textAlign: "center", marginTop: "24px" }}>
                <a href="#" onClick={(e) => { e.preventDefault(); setIsLogin(!isLogin); }}>
                  {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
                </a>
              </div>
              
              <div style={{ marginTop: "20px", borderTop: "1px solid var(--border)", paddingTop: "15px" }}>
                <h4 style={{ fontSize: "13px", color: "var(--text-muted)", marginBottom: "8px" }}>Quick Test Accounts:</h4>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  <div><strong>Patient:</strong> patient@clinic.com / patientpassword123</div>
                  <div><strong>Doctor:</strong> doctor@clinic.com / doctorpassword123</div>
                  <div><strong>Admin:</strong> admin@clinic.com / adminpassword123</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ==================== WELCOME BANNER ==================== */}
        {token && currentTab === "dashboard" && (
          <div className="welcome-banner">
            <h1>Hello, {userName}!</h1>
            <p>You are logged into the Aegis Health {role.toUpperCase()} Portal.</p>
          </div>
        )}

        {/* ==================== GOOGLE SYNC COMPONENT ==================== */}
        {token && currentTab === "dashboard" && (role === "patient" || role === "doctor") && (
          calendarConnected ? (
            <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "linear-gradient(135deg, #10b981 0%, #059669 100%)", color: "white", marginBottom: "32px" }}>
              <div>
                <h3 style={{ color: "white", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Icons.Check /> Linked to Google Calendar
                </h3>
                <p style={{ opacity: 0.9, fontSize: "14px", marginTop: "4px" }}>
                  Your clinic appointments will sync automatically.
                </p>
              </div>
              <button className="btn btn-outline" style={{ color: "white", borderColor: "rgba(255, 255, 255, 0.4)", backgroundColor: "rgba(255, 255, 255, 0.1)" }} onClick={handleGoogleDisconnect}>
                Disconnect Sync
              </button>
            </div>
          ) : (
            <div className="card google-sync-card" style={{ marginBottom: "32px" }}>
              <div>
                <h3>Connect to Google Calendar</h3>
                <p>Sync all your appointments and scheduling events dynamically to Google Calendar.</p>
              </div>
              <button className="btn btn-google" onClick={handleGoogleSync}>
                <Icons.Calendar /> Authorize Sync
              </button>
            </div>
          )
        )}

        {/* ==================== PATIENT TAB: DASHBOARD ==================== */}
        {token && role === "patient" && currentTab === "dashboard" && (
          <div>
            <h2 style={{ marginBottom: "20px" }}>My Appointment Schedule</h2>
            {patientAppointments.length === 0 ? (
              <div className="card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
                No appointments booked yet. Click "Book Slot" to schedule your first visit.
              </div>
            ) : (
              <div className="grid-2">
                {patientAppointments.map((appt) => (
                  <div key={appt.id} className="card">
                    <div className="card-title">
                      <h3>Dr. {appt.doctor_name}</h3>
                      <span className={`badge badge-status-${appt.status}`}>{appt.status.toUpperCase()}</span>
                    </div>
                    
                    <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "16px", fontSize: "14px", color: "var(--text-muted)" }}>
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <Icons.Calendar /> {appt.date}
                      </span>
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <Icons.Clock /> {appt.start_time} - {appt.end_time}
                      </span>
                    </div>

                    <div style={{ marginBottom: "12px" }}>
                      <strong>Reported Symptoms:</strong>
                      <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>{appt.symptoms || "None"}</p>
                    </div>

                    {appt.pre_visit_urgency && (
                      <div style={{ marginBottom: "12px" }}>
                        <strong>AI Symptom Urgency:</strong>
                        <span style={{ marginLeft: "8px" }} className={`badge badge-${appt.pre_visit_urgency.toLowerCase()}`}>
                          {appt.pre_visit_urgency}
                        </span>
                      </div>
                    )}

                    {appt.pre_visit_questions && appt.pre_visit_questions.length > 0 && (
                      <div className="questions-section">
                        <strong>AI Suggested Doctor Questions:</strong>
                        <ul className="questions-list">
                          {appt.pre_visit_questions.map((q, idx) => (
                            <li key={idx}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {appt.status === "completed" && (
                      <div className="clinical-section">
                        <strong>Doctor's Notes & Summary:</strong>
                        <p style={{ marginTop: "4px", fontSize: "14px" }}><strong>Notes:</strong> {appt.clinical_notes}</p>
                        <p style={{ marginTop: "4px", fontSize: "14px" }}><strong>Prescription:</strong> {appt.prescription}</p>
                        <div style={{ borderTop: "1px solid var(--border)", marginTop: "12px", paddingTop: "8px" }}>
                          <strong>Patient-Friendly AI Summary:</strong>
                          <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic", marginTop: "4px" }}>
                            {appt.post_visit_summary}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ==================== PATIENT TAB: REMINDERS ==================== */}
        {token && role === "patient" && currentTab === "reminders" && (
          <div>
            <h2 style={{ marginBottom: "20px" }}>Medication Reminder Tracker</h2>
            {patientReminders.length === 0 ? (
              <div className="card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
                No active medication reminders. Reminders are generated automatically when a doctor submits prescriptions.
              </div>
            ) : (
              <div className="grid-3 animate-fade-in">
                {patientReminders.map((rem) => {
                  const isTaken = !!takenReminders[rem.id];
                  return (
                    <div 
                      key={rem.id} 
                      className={`card ${isTaken ? "card-completed-pulse" : ""}`} 
                      style={{ 
                        borderLeft: isTaken ? "4px solid var(--success)" : "4px solid var(--accent)",
                        opacity: isTaken ? 0.85 : 1
                      }}
                    >
                      <div className="card-title">
                        <h3>{rem.medication_name}</h3>
                        <span 
                          className="prescription-tag" 
                          style={{ 
                            backgroundColor: isTaken ? "var(--success-light)" : "#f3e8ff", 
                            color: isTaken ? "var(--success)" : "#6b21a8" 
                          }}
                        >
                          {isTaken ? "TAKEN TODAY" : "ACTIVE"}
                        </span>
                      </div>
                      <div style={{ fontSize: "14px", marginBottom: "12px" }}>
                        <div><strong>Dosage:</strong> {rem.dosage}</div>
                        <div><strong>Schedule:</strong> Every {rem.frequency_hours} hours</div>
                      </div>
                      <div style={{ borderTop: "1px solid var(--border)", paddingTop: "12px", fontSize: "12px", color: "var(--text-muted)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        {isTaken ? (
                          <div>
                            <div>Completed dose at:</div>
                            <strong>{takenReminders[rem.id]}</strong>
                          </div>
                        ) : (
                          <div>
                            <div>Next Reminder Due:</div>
                            <strong>{new Date(rem.next_due_at + "Z").toLocaleString()}</strong>
                          </div>
                        )}
                        
                        {!isTaken && (
                          <button 
                            className="btn btn-outline" 
                            style={{ padding: "6px 12px", fontSize: "12px", height: "fit-content" }}
                            onClick={() => handleMarkTaken(rem.id)}
                          >
                            <Icons.Check /> Mark Taken
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ==================== PATIENT TAB: BOOK SLOT ==================== */}
        {token && role === "patient" && currentTab === "book" && (
          <div>
            <h2 style={{ marginBottom: "20px" }}>Schedule a Medical Consultation</h2>

            {/* Hold countdown lock indicator */}
            {activeHold && (
              <div className="alert alert-warning" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>Slot Hold Active!</strong> Your selected slot on {activeHold.date} at {activeHold.start_time} is reserved. Complete the symptoms form below to confirm booking.
                </div>
                <div style={{ fontWeight: "700", fontSize: "16px", backgroundColor: "#fff", padding: "4px 12px", borderRadius: "var(--radius-sm)", color: "var(--warning)" }}>
                  {formatTime(holdTimeRemaining)}
                </div>
              </div>
            )}

            <div className="grid-2" style={{ alignItems: "start" }}>
              {/* Doctor Search & Slots List */}
              <div className="card">
                <h3>1. Choose Doctor & Date</h3>
                
                <div className="form-group" style={{ marginTop: "16px", display: "flex", gap: "12px" }}>
                  <input 
                    type="text" 
                    className="form-input" 
                    placeholder="Search by specialty (e.g. Diagnostic)..." 
                    value={searchSpeciality}
                    onChange={(e) => setSearchSpeciality(e.target.value)}
                  />
                  <button className="btn btn-outline" onClick={() => fetchDoctors(searchSpeciality)}>
                    <Icons.Search /> Search
                  </button>
                </div>

                <div className="form-group">
                  <label className="form-label">Available Doctors</label>
                  <select 
                    className="form-select" 
                    value={selectedDoctor ? selectedDoctor.id : ""}
                    onChange={(e) => {
                      const doc = doctorsList.find(d => d.id === parseInt(e.target.value));
                      setSelectedDoctor(doc);
                      if (doc) fetchSlots(doc.id, selectedDate);
                    }}
                  >
                    <option value="">-- Select a Doctor --</option>
                    {doctorsList.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        Dr. {doc.full_name} ({doc.specialisation})
                      </option>
                    ))}
                  </select>
                </div>

                {selectedDoctor && (
                  <div className="form-group">
                    <label className="form-label">Select Date</label>
                    <input 
                      type="date" 
                      className="form-input" 
                      value={selectedDate}
                      min={new Date().toISOString().split("T")[0]}
                      onChange={(e) => {
                        setSelectedDate(e.target.value);
                        fetchSlots(selectedDoctor.id, e.target.value);
                      }}
                    />
                  </div>
                )}

                {selectedDoctor && (
                  <div style={{ marginTop: "24px" }}>
                    <h4>Select Available Slot ({selectedDoctor.slot_duration} min duration)</h4>
                    {availableSlots.length === 0 ? (
                      <p style={{ color: "var(--text-muted)", fontSize: "14px", marginTop: "8px" }}>
                        No working slots available on this date or doctor is on leave.
                      </p>
                    ) : (
                      <div className="slots-container">
                        {availableSlots.map((slot, index) => {
                          const isHeldByMe = activeHold && activeHold.start_time === slot.start_time;
                          const isHeldByOther = slot.status === "held" && !isHeldByMe;
                          
                          let className = "slot-item available";
                          if (slot.status === "booked") className = "slot-item booked";
                          else if (isHeldByOther) className = "slot-item booked"; // Treat as locked
                          else if (isHeldByMe) className = "slot-item held-by-me";
                          else if (slot.status === "held") className = "slot-item held";

                          return (
                            <div 
                              key={index} 
                              className={className}
                              onClick={() => {
                                if (slot.status === "available") {
                                  handleHoldSlot(slot);
                                }
                              }}
                            >
                              {slot.start_time}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Symptom Input Form */}
              <div className="card" id="booking-details-form">
                <h3>2. Complete Appointment Details</h3>
                <form onSubmit={handleBookAppointment} style={{ marginTop: "16px" }}>
                  <div className="form-group">
                    <label className="form-label">Selected Session Details</label>
                    {activeHold ? (
                      <div style={{ padding: "12px", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", backgroundColor: "var(--bg-app)", fontSize: "14px" }}>
                        <div><strong>Doctor:</strong> Dr. {selectedDoctor?.full_name}</div>
                        <div><strong>Date:</strong> {activeHold.date}</div>
                        <div><strong>Time:</strong> {activeHold.start_time} - {activeHold.end_time}</div>
                      </div>
                    ) : (
                      <p style={{ color: "var(--text-light)", fontStyle: "italic", fontSize: "14px" }}>
                        Please select an available slot on the left to lock your time.
                      </p>
                    )}
                  </div>

                  <div className="form-group">
                    <label className="form-label">Describe Symptoms & Pre-visit Details</label>
                    <textarea 
                      className="form-textarea" 
                      placeholder="Provide details about your symptoms (e.g. Mild headache and cough for 3 days)..."
                      value={symptomsText}
                      onChange={(e) => setSymptomsText(e.target.value)}
                      disabled={!activeHold}
                      required
                    ></textarea>
                  </div>

                  <button 
                    type="submit" 
                    className="btn btn-primary btn-block" 
                    disabled={!activeHold || bookingLoading}
                  >
                    {bookingLoading ? "Analyzing Symptoms & Booking..." : "Confirm Schedule Booking"}
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

        {/* ==================== DOCTOR TAB: DASHBOARD ==================== */}
        {token && role === "doctor" && currentTab === "dashboard" && (
          <div>
            <h2 style={{ marginBottom: "20px" }}>My Consultation Calendar</h2>
            {doctorAppointments.length === 0 ? (
              <div className="card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
                No appointments booked yet.
              </div>
            ) : (
              <div className="grid-2">
                {doctorAppointments.map((appt) => (
                  <div key={appt.id} className="card">
                    <div className="card-title">
                      <h3>Patient: {appt.patient_name}</h3>
                      <span className={`badge badge-status-${appt.status}`}>{appt.status.toUpperCase()}</span>
                    </div>

                    <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "16px", fontSize: "14px", color: "var(--text-muted)" }}>
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <Icons.Calendar /> {appt.date}
                      </span>
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <Icons.Clock /> {appt.start_time} - {appt.end_time}
                      </span>
                    </div>

                    <div style={{ marginBottom: "12px" }}>
                      <strong>Chief Complaint:</strong>
                      <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>{appt.pre_visit_complaint || appt.symptoms || "None"}</p>
                    </div>

                    {appt.pre_visit_urgency && (
                      <div style={{ marginBottom: "16px" }}>
                        <strong>AI Symptoms Urgency:</strong>
                        <span style={{ marginLeft: "8px" }} className={`badge badge-${appt.pre_visit_urgency.toLowerCase()}`}>
                          {appt.pre_visit_urgency}
                        </span>
                      </div>
                    )}

                    {appt.pre_visit_questions && appt.pre_visit_questions.length > 0 && appt.status === "booked" && (
                      <div className="questions-section" style={{ marginBottom: "16px" }}>
                        <strong>AI Suggested Screening Questions:</strong>
                        <ul className="questions-list">
                          {appt.pre_visit_questions.map((q, idx) => (
                            <li key={idx}>{q}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {appt.status === "booked" && (
                      <button className="btn btn-primary btn-block" onClick={() => setActiveNoteAppt(appt)}>
                        <Icons.Plus /> Complete Consultation & Add Notes
                      </button>
                    )}

                    {appt.status === "completed" && (
                      <div className="clinical-section">
                        <strong>My Notes & Prescriptions:</strong>
                        <p style={{ marginTop: "4px", fontSize: "14px" }}><strong>Notes:</strong> {appt.clinical_notes}</p>
                        <p style={{ marginTop: "4px", fontSize: "14px" }}><strong>Prescription:</strong> {appt.prescription}</p>
                        <div style={{ borderTop: "1px solid var(--border)", marginTop: "12px", paddingTop: "8px" }}>
                          <strong>Patient-Friendly AI Summary Generated:</strong>
                          <p style={{ fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic", marginTop: "4px" }}>
                            {appt.post_visit_summary}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Clinical Notes Modal */}
            {activeNoteAppt && (
              <div className="modal-overlay">
                <div className="modal-content">
                  <h3>Consultation Notes: {activeNoteAppt.patient_name}</h3>
                  <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "20px" }}>
                    Completed on {activeNoteAppt.date} at {activeNoteAppt.start_time}
                  </p>
                  
                  <form onSubmit={handlePostVisitNotes}>
                    <div className="form-group">
                      <label className="form-label">Clinical Observations (Notes)</label>
                      <textarea 
                        className="form-textarea" 
                        value={clinicalNotes} 
                        onChange={(e) => setClinicalNotes(e.target.value)}
                        placeholder="Detail the clinical observations, diagnosis, and instructions..."
                        required
                      ></textarea>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Prescription (Enter medications one per line in format: Name - Dosage - Instructions)</label>
                      <textarea 
                        className="form-textarea" 
                        value={prescription} 
                        onChange={(e) => setPrescription(e.target.value)}
                        placeholder="Paracetamol - 1 tablet - 8 hours&#10;Amoxicillin - 5ml suspension - 12 hours"
                        required
                      ></textarea>
                      <small style={{ color: "var(--text-light)", fontSize: "12px" }}>
                        Format guidelines: <strong>Medication - Dose - Frequency (e.g. 8 hours)</strong>. The system automatically structures background reminders from this text.
                      </small>
                    </div>

                    <div className="modal-footer">
                      <button type="button" className="btn btn-outline" onClick={() => setActiveNoteAppt(null)}>
                        Cancel
                      </button>
                      <button type="submit" className="btn btn-primary" disabled={postVisitLoading}>
                        {postVisitLoading ? "Generating AI Summary..." : "Submit & Complete"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== ADMIN TAB: DASHBOARD ==================== */}
        {token && role === "admin" && currentTab === "dashboard" && (
          <div>
            <h2 style={{ marginBottom: "20px" }}>Doctor Management</h2>
            {adminDoctors.length === 0 ? (
              <div className="card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
                No doctors registered. Go to "Register Doctor" tab to add staff.
              </div>
            ) : (
              <div className="grid-3">
                {adminDoctors.map((doc) => (
                  <div key={doc.id} className="card">
                    <div className="card-title">
                      <h3>Dr. {doc.full_name}</h3>
                      <span className="badge badge-low">{doc.specialisation}</span>
                    </div>
                    <div style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "16px" }}>
                      <div><strong>Email:</strong> {doc.email}</div>
                      <div><strong>Slot Duration:</strong> {doc.slot_duration} minutes</div>
                      <div style={{ marginTop: "8px" }}>
                        <strong>Active Leave Dates:</strong>
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "4px" }}>
                          {doc.leave_days.length === 0 ? (
                            <span style={{ fontStyle: "italic", fontSize: "12px" }}>No registered leaves</span>
                          ) : (
                            doc.leave_days.map((l, i) => (
                              <span key={i} className="badge badge-high" style={{ fontSize: "10px" }}>{l}</span>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                    <button className="btn btn-outline btn-block" onClick={() => setEditingDoctor(doc)}>
                      Configure Profile
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Edit Doctor Config Modal */}
            {editingDoctor && (
              <div className="modal-overlay">
                <div className="modal-content">
                  <h3>Configure Dr. {editingDoctor.full_name}</h3>
                  <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "20px" }}>
                    Configure working hours, slot interval durations, and specialization.
                  </p>
                  
                  <form onSubmit={handleUpdateDoctorConfig}>
                    <div className="form-group">
                      <label className="form-label">Specialisation</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={editingDoctor.specialisation} 
                        onChange={(e) => setEditingDoctor({ ...editingDoctor, specialisation: e.target.value })}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Slot Duration (Minutes)</label>
                      <input 
                        type="number" 
                        className="form-input" 
                        value={editingDoctor.slot_duration} 
                        onChange={(e) => setEditingDoctor({ ...editingDoctor, slot_duration: e.target.value })}
                        min="10"
                        max="120"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">Biography</label>
                      <textarea 
                        className="form-textarea" 
                        value={editingDoctor.bio || ""} 
                        onChange={(e) => setEditingDoctor({ ...editingDoctor, bio: e.target.value })}
                      ></textarea>
                    </div>

                    <div className="modal-footer">
                      <button type="button" className="btn btn-outline" onClick={() => setEditingDoctor(null)}>
                        Cancel
                      </button>
                      <button type="submit" className="btn btn-primary">
                        Save Configuration
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== ADMIN TAB: REGISTER DOCTOR ==================== */}
        {token && role === "admin" && currentTab === "add_doctor" && (
          <div style={{ maxWidth: "560px", margin: "0 auto" }}>
            <div className="card">
              <h2>Register New Doctor User</h2>
              <p style={{ color: "var(--text-muted)", marginBottom: "24px" }}>
                Add new credentials to the system. This creates a basic doctor user account.
              </p>
              
              <form onSubmit={handleAddDoctor}>
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={newDoctorName} 
                    onChange={(e) => setNewDoctorName(e.target.value)} 
                    placeholder="Dr. Gregory House"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Email Address</label>
                  <input 
                    type="email" 
                    className="form-input" 
                    value={newDoctorEmail} 
                    onChange={(e) => setNewDoctorEmail(e.target.value)} 
                    placeholder="house@clinic.com"
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input 
                    type="password" 
                    className="form-input" 
                    value={newDoctorPassword} 
                    onChange={(e) => setNewDoctorPassword(e.target.value)} 
                    placeholder="••••••••"
                    required
                  />
                </div>

                <button type="submit" className="btn btn-primary btn-block">
                  Create Doctor Account
                </button>
              </form>
            </div>
          </div>
        )}

        {/* ==================== ADMIN TAB: LEAVE MANAGEMENT ==================== */}
        {token && role === "admin" && currentTab === "leaves" && (
          <div>
            <h2>Manage Doctor Leaves</h2>
            <p style={{ color: "var(--text-muted)", marginBottom: "24px" }}>
              Declare doctor leave dates. Existing bookings on leave dates will be automatically cancelled, and affected patients will receive notification emails immediately.
            </p>

            <div className="grid-2" style={{ alignItems: "start" }}>
              <div className="card">
                <h3>Declare Doctor Leave</h3>
                <form onSubmit={handleAddLeave} style={{ marginTop: "16px" }}>
                  <div className="form-group">
                    <label className="form-label">Select Doctor</label>
                    <select 
                      className="form-select" 
                      value={adminSelectedDoctorId}
                      onChange={(e) => setAdminSelectedDoctorId(e.target.value)}
                      required
                    >
                      <option value="">-- Choose Doctor --</option>
                      {adminDoctors.map((doc) => (
                        <option key={doc.id} value={doc.id}>
                          Dr. {doc.full_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Leave Date</label>
                    <input 
                      type="date" 
                      className="form-input" 
                      value={leaveDateInput}
                      min={new Date().toISOString().split("T")[0]}
                      onChange={(e) => setLeaveDateInput(e.target.value)}
                      required
                    />
                  </div>

                  <div className="alert alert-warning" style={{ fontSize: "12px", marginBottom: "16px" }}>
                    Warning: Declaring leave will permanently cancel conflicting patient slots and send email notices immediately.
                  </div>

                  <button type="submit" className="btn btn-danger btn-block">
                    Add Leave Date
                  </button>
                </form>
              </div>

              {/* View/Remove Leaves */}
              <div className="card">
                <h3>Active Leave Schedule</h3>
                <div style={{ marginTop: "16px" }}>
                  {adminDoctors.length === 0 ? (
                    <p style={{ color: "var(--text-muted)" }}>No doctor profiles available</p>
                  ) : (
                    adminDoctors.map((doc) => {
                      if (doc.leave_days.length === 0) return null;
                      return (
                        <div key={doc.id} style={{ marginBottom: "20px", borderBottom: "1px solid var(--border)", pb: "16px" }}>
                          <h4 style={{ fontSize: "15px", marginBottom: "8px" }}>Dr. {doc.full_name}</h4>
                          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                            {doc.leave_days.map((date) => (
                              <div key={date} className="badge badge-high" style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 12px" }}>
                                <span>{date}</span>
                                <span 
                                  style={{ cursor: "pointer", fontWeight: "800", color: "#b91c1c", fontSize: "14px" }}
                                  onClick={() => handleRemoveLeave(doc.id, date)}
                                >
                                  ×
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }).filter(Boolean).length === 0 && (
                      <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>No active leaves scheduled across clinic doctors.</p>
                    )
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
