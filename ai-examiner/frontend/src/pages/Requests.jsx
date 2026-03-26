import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import API from "../services/api";
import { theme } from "../theme/theme";

export default function Requests() {
  const [requests, setRequests]     = useState([]);
  const [loading, setLoading]       = useState(true);
  const [filter, setFilter]         = useState("all");
  const [remarks, setRemarks]       = useState({});
  const [actionLoading, setActionLoading] = useState({});

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const res = await API.get("/student/requests/all");
      setRequests(res.data);
    } catch (err) {
      console.error("Failed to load requests", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleAction = async (requestId, action) => {
    const remark = remarks[requestId] || "";
    setActionLoading(prev => ({ ...prev, [requestId]: true }));

    try {
      await API.put(
        `/student/requests/${requestId}/${action}?faculty_remark=${encodeURIComponent(remark)}`
      );
      await fetchRequests();
    } catch (err) {
      alert(err.response?.data?.detail || "Action failed");
    } finally {
      setActionLoading(prev => ({ ...prev, [requestId]: false }));
    }
  };

  const filtered = requests.filter(r => {
    if (filter === "all")      return true;
    if (filter === "pending")  return r.status === "pending";
    if (filter === "approved") return r.status === "approved";
    if (filter === "rejected") return r.status === "rejected";
    return true;
  });

  const pendingCount  = requests.filter(r => r.status === "pending").length;
  const approvedCount = requests.filter(r => r.status === "approved").length;
  const rejectedCount = requests.filter(r => r.status === "rejected").length;

  return (
    <div style={wrapper}>

      {/* HEADER */}
      <div style={header}>
        <div>
          <h2 style={title}>Student Requests</h2>
          <p style={subtitle}>Manage photocopy and revaluation requests from students</p>
        </div>
        <button onClick={fetchRequests} style={refreshBtn}>↻ Refresh</button>
      </div>

      {/* STATS */}
      <div style={statsGrid}>
        <StatCard label="Total"    value={requests.length} color="#64748b" />
        <StatCard label="Pending"  value={pendingCount}    color="#d97706" />
        <StatCard label="Approved" value={approvedCount}   color="#16a34a" />
        <StatCard label="Rejected" value={rejectedCount}   color="#dc2626" />
      </div>

      {/* FILTER TABS */}
      <div style={filterRow}>
        {["all", "pending", "approved", "rejected"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              ...filterBtn,
              background: filter === f ? theme.colors.primary : "white",
              color:      filter === f ? "white" : "#555"
            }}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f === "pending" && pendingCount > 0 && (
              <span style={badge}>{pendingCount}</span>
            )}
          </button>
        ))}
      </div>

      {/* REQUESTS LIST */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px", color: "#888" }}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1 }}
            style={spinner}
          />
          <div style={{ marginTop: "12px" }}>Loading requests...</div>
        </div>
      ) : filtered.length === 0 ? (
        <div style={emptyBox}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>📭</div>
          <div>No {filter === "all" ? "" : filter} requests found.</div>
        </div>
      ) : (
        filtered.map(r => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={requestCard}
          >
            {/* CARD HEADER */}
            <div style={cardHeader}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ fontSize: "22px" }}>
                  {r.request_type === "photocopy" ? "📄" : "🔄"}
                </span>
                <div>
                  <div style={cardTitle}>
                    {r.request_type === "photocopy" ? "Photocopy Request" : "Revaluation Request"}
                  </div>
                  <div style={cardMeta}>
                    Roll No: <strong>{r.roll_number}</strong> &nbsp;·&nbsp;
                    Submission ID: {r.submission_id} &nbsp;·&nbsp;
                    {new Date(r.requested_at).toLocaleDateString("en-IN", {
                      day: "numeric", month: "short", year: "numeric"
                    })}
                  </div>
                </div>
              </div>

              <span style={{
                ...statusBadge,
                background: r.status === "pending"  ? "#fff3cd"
                          : r.status === "approved" ? "#d1fae5"
                          : "#fee2e2",
                color:      r.status === "pending"  ? "#856404"
                          : r.status === "approved" ? "#065f46"
                          : "#991b1b"
              }}>
                {r.status.toUpperCase()}
              </span>
            </div>

            {/* REASON */}
            {r.reason && (
              <div style={reasonBox}>
                <span style={{ fontWeight: "600", fontSize: "12px" }}>Student Reason: </span>
                <span style={{ fontSize: "12px", color: "#555" }}>{r.reason}</span>
              </div>
            )}

            {/* FACULTY REMARK (if resolved) */}
            {r.faculty_remark && (
              <div style={remarkBox}>
                <span style={{ fontWeight: "600", fontSize: "12px" }}>Your Remark: </span>
                <span style={{ fontSize: "12px", color: "#555" }}>{r.faculty_remark}</span>
              </div>
            )}

            {/* REVALUATION NOTE */}
            {r.request_type === "revaluation" && r.status === "approved" && (
              <div style={infoBox}>
                ✅ Revaluation was triggered automatically when this request was approved.
              </div>
            )}

            {/* PHOTOCOPY NOTE */}
            {r.request_type === "photocopy" && r.status === "approved" && (
              <div style={infoBox}>
                ✅ Student can now download the watermarked photocopy PDF from their portal.
              </div>
            )}

            {/* ACTIONS — only for pending */}
            {r.status === "pending" && (
              <div style={actionsRow}>
                <input
                  type="text"
                  placeholder="Add remark (optional)"
                  value={remarks[r.id] || ""}
                  onChange={e => setRemarks(prev => ({ ...prev, [r.id]: e.target.value }))}
                  style={remarkInput}
                />
                <button
                  onClick={() => handleAction(r.id, "approve")}
                  disabled={actionLoading[r.id]}
                  style={approveBtn}
                >
                  {actionLoading[r.id] ? "..." : "✓ Approve"}
                </button>
                <button
                  onClick={() => handleAction(r.id, "reject")}
                  disabled={actionLoading[r.id]}
                  style={rejectBtn}
                >
                  {actionLoading[r.id] ? "..." : "✗ Reject"}
                </button>
              </div>
            )}
          </motion.div>
        ))
      )}
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <motion.div whileHover={{ y: -4 }} style={statCard}>
      <div style={{ fontSize: "28px", fontWeight: "700", color }}>{value}</div>
      <div style={{ fontSize: "13px", color: "#888", marginTop: "4px" }}>{label}</div>
    </motion.div>
  );
}

/* ================= STYLES ================= */

const wrapper     = { maxWidth: "1000px", margin: "0 auto", padding: "20px" };
const header      = { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "30px" };
const title       = { fontSize: "28px", fontWeight: "700", color: theme.colors.primary };
const subtitle    = { color: "#64748b", marginTop: "6px", fontSize: "14px" };
const refreshBtn  = { padding: "8px 18px", borderRadius: "10px", border: "1px solid #ddd", background: "white", cursor: "pointer", fontSize: "13px" };
const statsGrid   = { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "24px" };
const statCard    = { background: "white", padding: "20px", borderRadius: "14px", boxShadow: "0 10px 30px rgba(0,0,0,0.05)", textAlign: "center" };
const filterRow   = { display: "flex", gap: "10px", marginBottom: "24px", flexWrap: "wrap" };
const filterBtn   = { padding: "8px 20px", borderRadius: "20px", border: "1px solid #ddd", cursor: "pointer", fontSize: "13px", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" };
const badge       = { background: "#dc2626", color: "white", borderRadius: "99px", padding: "1px 7px", fontSize: "11px" };
const requestCard = { background: "white", padding: "20px 24px", borderRadius: "14px", boxShadow: "0 10px 30px rgba(0,0,0,0.06)", marginBottom: "16px" };
const cardHeader  = { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" };
const cardTitle   = { fontWeight: "600", fontSize: "15px", color: "#1e293b" };
const cardMeta    = { fontSize: "12px", color: "#888", marginTop: "3px" };
const statusBadge = { padding: "4px 14px", borderRadius: "20px", fontSize: "11px", fontWeight: "700", whiteSpace: "nowrap" };
const reasonBox   = { background: "#f8f9fa", padding: "10px 14px", borderRadius: "8px", marginBottom: "10px" };
const remarkBox   = { background: "#f0f9ff", padding: "10px 14px", borderRadius: "8px", marginBottom: "10px" };
const infoBox     = { background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "8px", padding: "10px 14px", fontSize: "12px", color: "#166534", marginBottom: "10px" };
const actionsRow  = { display: "flex", gap: "10px", alignItems: "center", marginTop: "12px", flexWrap: "wrap" };
const remarkInput = { flex: 1, padding: "9px 14px", borderRadius: "10px", border: "1px solid #ddd", fontSize: "13px", minWidth: "200px" };
const approveBtn  = { padding: "9px 20px", borderRadius: "10px", border: "none", background: "#16a34a", color: "white", cursor: "pointer", fontWeight: "600", fontSize: "13px" };
const rejectBtn   = { padding: "9px 20px", borderRadius: "10px", border: "none", background: "#dc2626", color: "white", cursor: "pointer", fontWeight: "600", fontSize: "13px" };
const emptyBox    = { textAlign: "center", padding: "60px", color: "#aaa", background: "white", borderRadius: "14px" };
const spinner     = { width: "28px", height: "28px", border: "3px solid #eee", borderTop: `3px solid ${theme.colors.primary}`, borderRadius: "50%", margin: "0 auto" };