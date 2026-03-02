import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import API from "../services/api";
import { theme } from "../theme/theme";

export default function ExamDetails() {
  const { examId } = useParams();

  const [exam, setExam] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const [uploadState, setUploadState] = useState({
    "question-paper": { loading: false, fileName: "", success: false },
    "model-answer": { loading: false, fileName: "", success: false },
    "submit-answer-sheet": { loading: false, fileName: "", success: false }
  });

  const fileRefs = {
    "question-paper": useRef(null),
    "model-answer": useRef(null),
    "submit-answer-sheet": useRef(null)
  };

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

  /* ================= UPLOAD ================= */

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

  if (loading) return <p>Loading exam details...</p>;
  if (!exam) return <p>Exam not found.</p>;

  const statusColors = {
    draft: "#999",
    published: "#d97706",
    locked: "#16a34a"
  };

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

        <span
          style={{
            ...statusBadge,
            background: statusColors[exam.result_status]
          }}
        >
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
            background:
              exam.result_status === "locked"
                ? "#ccc"
                : theme.colors.primary
          }}
        >
          Publish Result
        </button>

        <button
          onClick={handleLock}
          disabled={exam.result_status !== "published" || actionLoading}
          style={{
            ...actionBtn,
            background:
              exam.result_status !== "published"
                ? "#ccc"
                : theme.colors.danger
          }}
        >
          Lock Result
        </button>
      </div>

      {/* ================= UPLOAD SECTION ================= */}
      <div style={uploadWrapper}>
        {[
          { label: "Question Paper", type: "question-paper" },
          { label: "Model Answer", type: "model-answer" },
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
                onChange={(e) =>
                  handleUpload(item.type, e.target.files[0])
                }
              />
            </motion.div>
          );
        })}
      </div>

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
  marginBottom: "25px"
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

const uploadTitle = {
  fontWeight: 600,
  fontSize: "14px"
};

const contentArea = {
  height: "40px",
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "center"
};

const fileNameStyle = {
  fontSize: "12px",
  maxWidth: "150px",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap"
};

const spinner = {
  width: "20px",
  height: "20px",
  border: "3px solid #eee",
  borderTop: `3px solid ${theme.colors.primary}`,
  borderRadius: "50%"
};

const successText = {
  fontSize: "12px",
  color: "#16a34a",
  fontWeight: "600"
};

const dropText = {
  fontSize: "11px",
  color: "#888"
};

const tableCard = {
  background: "white",
  borderRadius: "14px",
  boxShadow: theme.shadow.soft,
  overflowX: "auto"
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse"
};

const theadStyle = {
  background: theme.colors.primary,
  color: "white"
};

const th = { padding: "12px", textAlign: "center" };
const td = { padding: "12px", textAlign: "center" };