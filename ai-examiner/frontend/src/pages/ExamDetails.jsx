import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import API from "../services/api";
import { theme } from "../theme/theme";

export default function ExamDetails() {
  const { examId } = useParams();

  const [exam, setExam]             = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const [uploadState, setUploadState] = useState({
    "question-paper":      { loading: false, fileName: "", success: false },
    "model-answer":        { loading: false, fileName: "", success: false },
    "submit-answer-sheet": { loading: false, fileName: "", success: false }
  });

  // ── Bulk upload state ──────────────────────────────────────
  const [bulkState, setBulkState] = useState({
    phase:      "idle",      // idle | uploading | processing | done | failed
    isDragging: false,
    jobId:      null,
    total:      0,
    processed:  0,
    succeeded:  0,
    failed:     0,
    percent:    0,
    results:    []
  });

  const pollRef     = useRef(null);   // holds setInterval id
  const fileRefs    = {
    "question-paper":      useRef(null),
    "model-answer":        useRef(null),
    "submit-answer-sheet": useRef(null)
  };
  const bulkFileRef   = useRef(null);
  const bulkFolderRef = useRef(null);

  /* ================= FETCH ================= */

  const fetchExam = async () => {
    const res = await API.get(`/exams/${examId}`);
    setExam(res.data);
  };

  const fetchSubmissions = async () => {
    const res = await API.get(`/exams/${examId}/submissions`);
    setSubmissions(res.data);
  };

  const fetchAll = async () => {
    setLoading(true);
    await Promise.all([fetchExam(), fetchSubmissions()]);
    setLoading(false);
  };

  useEffect(() => {
    fetchAll();
    // cleanup polling on unmount
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [examId]);

  /* ================= RESULT ACTIONS ================= */

  const handlePublish = async () => {
    try {
      setActionLoading(true);
      await API.put(`/exams/${examId}/publish-result`);
      await fetchExam();
    } catch (err) {
      setError(err.response?.data?.detail || "Publish failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleLock = async () => {
    try {
      setActionLoading(true);
      await API.put(`/exams/${examId}/lock-result`);
      await fetchExam();
    } catch (err) {
      setError(err.response?.data?.detail || "Lock failed.");
    } finally {
      setActionLoading(false);
    }
  };

  /* ================= SINGLE UPLOAD ================= */

  const handleUpload = async (type, file) => {
    if (!file) return;

    setUploadState(prev => ({
      ...prev,
      [type]: { loading: true, fileName: file.name, success: false }
    }));

    const formData = new FormData();
    formData.append("file", file);

    try {
      const uploadRes = await API.post(
        `/exams/${examId}/${type}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      if (type === "submit-answer-sheet") {
        const submissionId = uploadRes.data.submission_id;
        await API.post(`/exams/${examId}/evaluate/${submissionId}`);
      }

      setUploadState(prev => ({
        ...prev,
        [type]: { loading: false, fileName: file.name, success: true }
      }));

      fetchSubmissions();

    } catch (err) {
      setUploadState(prev => ({
        ...prev,
        [type]: { loading: false, fileName: "", success: false }
      }));
      setError(err.response?.data?.detail || "Upload failed.");
    }
  };

  /* ================= BULK UPLOAD ================= */

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const startPolling = (jobId) => {
    stopPolling();

    pollRef.current = setInterval(async () => {
      try {
        const res = await API.get(`/exams/${examId}/bulk-job/${jobId}`);
        const d   = res.data;

        setBulkState(prev => ({
          ...prev,
          processed: d.processed,
          succeeded: d.succeeded,
          failed:    d.failed,
          percent:   d.percent,
          results:   d.results,
          phase:     d.status === "done" || d.status === "failed" ? d.status : "processing"
        }));

        // stop polling when job is finished
        if (d.status === "done" || d.status === "failed") {
          stopPolling();
          fetchSubmissions();
        }

      } catch (err) {
        stopPolling();
        setBulkState(prev => ({ ...prev, phase: "failed" }));
      }
    }, 3000);  // poll every 3 seconds
  };

  const handleBulkUpload = async (files) => {
    const pdfs = Array.from(files).filter(
      f => f.type === "application/pdf" || f.name.endsWith(".pdf")
    );

    if (pdfs.length === 0) {
      setError("No PDF files found. Please upload PDF files only.");
      return;
    }

    setError("");
    setBulkState({
      phase:      "uploading",
      isDragging: false,
      jobId:      null,
      total:      pdfs.length,
      processed:  0,
      succeeded:  0,
      failed:     0,
      percent:    0,
      results:    []
    });

    const formData = new FormData();
    pdfs.forEach(f => formData.append("files", f));

    try {
      // This returns immediately with job_id
      const res   = await API.post(
        `/exams/${examId}/bulk-submit-sheets`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      const jobId = res.data.job_id;

      setBulkState(prev => ({
        ...prev,
        phase: "processing",
        jobId
      }));

      // Start polling progress every 3 seconds
      startPolling(jobId);

    } catch (err) {
      setBulkState(prev => ({ ...prev, phase: "failed" }));
      setError(err.response?.data?.detail || "Bulk upload failed.");
    }
  };

  // Drag and drop handlers
  const handleDragOver  = (e) => { e.preventDefault(); setBulkState(p => ({ ...p, isDragging: true })); };
  const handleDragLeave = (e) => { e.preventDefault(); setBulkState(p => ({ ...p, isDragging: false })); };
  const handleDrop      = (e) => {
    e.preventDefault();
    setBulkState(p => ({ ...p, isDragging: false }));
    if (e.dataTransfer.files.length > 0) handleBulkUpload(e.dataTransfer.files);
  };

  const resetBulk = () => {
    stopPolling();
    setBulkState({
      phase: "idle", isDragging: false, jobId: null,
      total: 0, processed: 0, succeeded: 0, failed: 0, percent: 0, results: []
    });
  };

  if (loading) return <p>Loading exam details...</p>;
  if (!exam)   return <p>Exam not found.</p>;

  const statusColors = {
    draft:     "#999",
    published: "#d97706",
    locked:    "#16a34a"
  };

  const { phase, total, processed, succeeded, failed, percent, results } = bulkState;
  const isProcessing = phase === "uploading" || phase === "processing";

  return (
    <div style={pageWrapper}>

      {error && (
        <p style={{ color: theme.colors.danger, marginBottom: "15px" }}>
          {error}
        </p>
      )}

      {/* ================= HEADER ================= */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={headerCard}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <h2 style={titleStyle}>{exam.title}</h2>
          <div style={metaRow}>
            <span>Class: {exam.class_name}</span>
            <span>Division: {exam.division}</span>
            <span>Subject: {exam.subject}</span>
            <span>Total Marks: {exam.total_marks}</span>
          </div>
        </div>
        <span style={{ ...statusBadge, background: statusColors[exam.result_status] }}>
          {exam.result_status.toUpperCase()}
        </span>
      </motion.div>

      {/* ================= RESULT BUTTONS ================= */}
      <div style={buttonRow}>
        <button
          onClick={handlePublish}
          disabled={exam.result_status === "locked" || actionLoading}
          style={{
            ...actionBtn,
            background: exam.result_status === "locked" ? "#ccc" : theme.colors.primary
          }}
        >
          Publish Result
        </button>
        <button
          onClick={handleLock}
          disabled={exam.result_status !== "published" || actionLoading}
          style={{
            ...actionBtn,
            background: exam.result_status !== "published" ? "#ccc" : theme.colors.danger
          }}
        >
          Lock Result
        </button>
      </div>

      {/* ================= SINGLE UPLOAD CARDS ================= */}
      <div style={uploadWrapper}>
        {[
          { label: "Question Paper", type: "question-paper" },
          { label: "Model Answer",   type: "model-answer" },
          { label: "Student Answer", type: "submit-answer-sheet" }
        ].map((item) => {
          const state = uploadState[item.type];
          return (
            <motion.div
              key={item.type}
              whileHover={{ scale: 1.02 }}
              onClick={() => fileRefs[item.type].current.click()}
              style={uploadCard}
            >
              <div style={uploadTitle}>{item.label}</div>
              <div style={contentArea}>
                {state.loading && (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1 }}
                    style={spinner}
                  />
                )}
                {!state.loading && state.fileName && (
                  <div style={fileNameStyle}>📄 {state.fileName}</div>
                )}
                {!state.loading && state.success && (
                  <div style={successText}>Uploaded</div>
                )}
              </div>
              <div style={dropText}>Click to Upload</div>
              <input
                ref={fileRefs[item.type]}
                type="file"
                hidden
                onChange={(e) => handleUpload(item.type, e.target.files[0])}
              />
            </motion.div>
          );
        })}
      </div>

      {/* ================= BULK UPLOAD CARD ================= */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          ...bulkCard,
          border: bulkState.isDragging
            ? `2px dashed ${theme.colors.primary}`
            : "2px dashed #ddd",
          background: bulkState.isDragging ? "#f0f7ff" : "white"
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Title row */}
        <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
          <div style={uploadTitle}>📦 Bulk Answer Sheets</div>
          {(phase === "done" || phase === "failed") && (
            <button onClick={resetBulk} style={resetBtn}>Upload Again</button>
          )}
        </div>

        {/* ── IDLE ── */}
        {phase === "idle" && (
          <div style={{ textAlign: "center", color: "#888", fontSize: "13px" }}>
            Drag & drop PDFs here, or choose files below
          </div>
        )}

        {/* ── UPLOADING (sending files to server) ── */}
        {phase === "uploading" && (
          <div style={centerCol}>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1 }}
              style={spinner}
            />
            <div style={{ fontSize: "13px", color: "#555" }}>
              Uploading {total} files to server...
            </div>
          </div>
        )}

        {/* ── PROCESSING (background job running) ── */}
        {phase === "processing" && (
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "12px" }}>

            {/* Progress numbers */}
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", color: "#444" }}>
              <span>Checking papers...</span>
              <span style={{ fontWeight: 600 }}>{processed} / {total} done</span>
            </div>

            {/* Progress bar */}
            <div style={progressTrack}>
              <motion.div
                style={{ ...progressFill, background: theme.colors.primary }}
                initial={{ width: "0%" }}
                animate={{ width: `${percent}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>

            {/* Percent + counts */}
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
              <span style={{ color: theme.colors.primary, fontWeight: 600 }}>{percent}%</span>
              <span>
                <span style={{ color: "#16a34a", fontWeight: 600 }}>✅ {succeeded} ok</span>
                {failed > 0 && (
                  <span style={{ color: theme.colors.danger, fontWeight: 600 }}> &nbsp;·&nbsp; ❌ {failed} failed</span>
                )}
              </span>
            </div>

            {/* Live per-sheet results as they come in */}
            {results.length > 0 && (
              <div style={resultScroll}>
                {results
                  .filter(r => r.status === "done")
                  .map((r, i) => (
                    <div key={i} style={{
                      ...resultRow,
                      background: r.success ? "#f0fdf4" : "#fff1f2"
                    }}>
                      <span style={{ fontWeight: 600, fontSize: "12px" }}>
                        {r.success ? "✅" : "❌"} {r.filename}
                      </span>
                      {r.success ? (
                        <span style={{ fontSize: "11px", color: "#555" }}>
                          Roll: {r.roll_number} &nbsp;|&nbsp;
                          Marks: {r.total_marks}/{r.max_marks} &nbsp;|&nbsp;
                          {r.percentage}% &nbsp;|&nbsp; Grade: {r.grade}
                        </span>
                      ) : (
                        <span style={{ fontSize: "11px", color: theme.colors.danger }}>
                          {r.error}
                        </span>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* ── DONE ── */}
        {phase === "done" && (
          <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "12px" }}>

            {/* Completed progress bar */}
            <div style={progressTrack}>
              <div style={{ ...progressFill, width: "100%", background: "#16a34a" }} />
            </div>

            {/* Summary */}
            <div style={{ display: "flex", gap: "16px", fontSize: "13px", justifyContent: "center" }}>
              <span style={{ color: "#16a34a", fontWeight: 600 }}>✅ {succeeded} checked</span>
              {failed > 0 && (
                <span style={{ color: theme.colors.danger, fontWeight: 600 }}>❌ {failed} failed</span>
              )}
              <span style={{ color: "#888" }}>out of {total} sheets</span>
            </div>

            {/* Full results table */}
            <div style={resultScroll}>
              {results.map((r, i) => (
                <div key={i} style={{
                  ...resultRow,
                  background: r.success ? "#f0fdf4" : "#fff1f2"
                }}>
                  <span style={{ fontWeight: 600, fontSize: "12px" }}>
                    {r.success ? "✅" : "❌"} {r.filename}
                  </span>
                  {r.success ? (
                    <span style={{ fontSize: "11px", color: "#555" }}>
                      Roll: {r.roll_number} &nbsp;|&nbsp;
                      Marks: {r.total_marks}/{r.max_marks} &nbsp;|&nbsp;
                      {r.percentage}% &nbsp;|&nbsp; Grade: {r.grade}
                    </span>
                  ) : (
                    <span style={{ fontSize: "11px", color: theme.colors.danger }}>
                      {r.error}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── FAILED (unexpected crash) ── */}
        {phase === "failed" && (
          <div style={{ color: theme.colors.danger, fontSize: "13px", textAlign: "center" }}>
            Something went wrong. Please try again.
          </div>
        )}

        {/* Buttons — only show when idle or done */}
        {!isProcessing && phase !== "done" && (
          <div style={{ display: "flex", gap: "10px", justifyContent: "center", flexWrap: "wrap" }}>
            <button onClick={() => bulkFileRef.current.click()} style={bulkBtn}>
              📄 Choose Files
            </button>
            <button onClick={() => bulkFolderRef.current.click()} style={bulkBtn}>
              📁 Choose Folder
            </button>
          </div>
        )}

        {/* Hidden inputs */}
        <input
          ref={bulkFileRef}
          type="file"
          hidden
          multiple
          accept=".pdf"
          onChange={(e) => handleBulkUpload(e.target.files)}
        />
        <input
          ref={bulkFolderRef}
          type="file"
          hidden
          multiple
          accept=".pdf"
          webkitdirectory=""
          onChange={(e) => handleBulkUpload(e.target.files)}
        />

      </motion.div>

      {/* ================= TABLE ================= */}
      <div style={tableCard}>
        <table style={tableStyle}>
          <thead style={theadStyle}>
            <tr>
              <th style={th}>Roll No</th>
              <th style={th}>Obtained Marks</th>
              <th style={th}>Percentage</th>
              <th style={th}>Grade</th>
            </tr>
          </thead>
          <tbody>
            {submissions.map((s) => (
              <tr key={s.submission_id}>
                <td style={td}>{s.roll_number}</td>
                <td style={td}>{s.total_marks ?? "-"}</td>
                <td style={td}>{s.percentage ?? "-"}</td>
                <td style={td}>{s.grade ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </div>
  );
}

/* ================= STYLES ================= */

const pageWrapper = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "10px 20px 30px 20px"
};

const headerCard = {
  background: "white",
  padding: "18px 25px",
  borderRadius: "14px",
  boxShadow: theme.shadow.soft,
  marginBottom: "15px",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center"
};

const titleStyle = {
  color: theme.colors.primary,
  fontSize: "22px",
  fontWeight: "600",
  margin: 0
};

const metaRow = {
  display: "flex",
  gap: "20px",
  fontSize: "13px",
  color: "#555"
};

const statusBadge = {
  padding: "6px 14px",
  borderRadius: "20px",
  color: "white",
  fontSize: "12px",
  fontWeight: "600"
};

const buttonRow = {
  display: "flex",
  gap: "12px",
  marginBottom: "20px"
};

const actionBtn = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "none",
  fontSize: "13px",
  fontWeight: "500",
  color: "white",
  cursor: "pointer"
};

const uploadWrapper = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: "18px",
  marginBottom: "18px"
};

const uploadCard = {
  background: "white",
  padding: "15px",
  borderRadius: "14px",
  boxShadow: theme.shadow.soft,
  height: "170px",
  display: "flex",
  flexDirection: "column",
  justifyContent: "space-between",
  alignItems: "center",
  cursor: "pointer"
};

const bulkCard = {
  background: "white",
  padding: "20px",
  borderRadius: "14px",
  boxShadow: theme.shadow.soft,
  marginBottom: "25px",
  display: "flex",
  flexDirection: "column",
  gap: "14px",
  alignItems: "center",
  transition: "border 0.2s, background 0.2s"
};

const bulkBtn = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "1px solid #ddd",
  fontSize: "13px",
  fontWeight: "500",
  background: "white",
  cursor: "pointer"
};

const resetBtn = {
  padding: "5px 12px",
  borderRadius: "8px",
  border: "1px solid #ddd",
  fontSize: "12px",
  background: "white",
  cursor: "pointer",
  color: "#555"
};

const progressTrack = {
  width: "100%",
  height: "10px",
  background: "#f0f0f0",
  borderRadius: "99px",
  overflow: "hidden"
};

const progressFill = {
  height: "100%",
  borderRadius: "99px"
};

const centerCol = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "10px"
};

const resultScroll = {
  maxHeight: "180px",
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  width: "100%"
};

const resultRow = {
  display: "flex",
  flexDirection: "column",
  gap: "2px",
  padding: "8px 12px",
  borderRadius: "8px",
  fontSize: "12px"
};

const uploadTitle  = { fontWeight: 600, fontSize: "14px" };
const contentArea  = { height: "40px", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center" };
const fileNameStyle = { fontSize: "12px", maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
const spinner      = { width: "20px", height: "20px", border: "3px solid #eee", borderTop: `3px solid ${theme.colors.primary}`, borderRadius: "50%" };
const successText  = { fontSize: "12px", color: "#16a34a", fontWeight: "600" };
const dropText     = { fontSize: "11px", color: "#888" };
const tableCard    = { background: "white", borderRadius: "14px", boxShadow: theme.shadow.soft, overflowX: "auto" };
const tableStyle   = { width: "100%", borderCollapse: "collapse" };
const theadStyle   = { background: theme.colors.primary, color: "white" };
const th           = { padding: "12px", textAlign: "center" };
const td           = { padding: "12px", textAlign: "center" };