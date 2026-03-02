import { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid
} from "recharts";

import API from "../services/api";
import { theme } from "../theme/theme";

export default function ResultsPage() {
  const [exams, setExams] = useState([]);
  const [selectedExam, setSelectedExam] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [search, setSearch] = useState("");

  /* ================= FETCH EXAMS ================= */

  useEffect(() => {
    const fetchExams = async () => {
      const res = await API.get("/exams");
      setExams(res.data);
    };
    fetchExams();
  }, []);

  /* ================= LOAD SUBMISSIONS ================= */

  const loadExamResults = async (exam) => {
    setSelectedExam(exam);
    setSelectedSubmission(null);
    const res = await API.get(`/exams/${exam.id}/submissions`);
    setSubmissions(res.data);
  };

  /* ================= LOAD MARKSHEET ================= */

  const loadMarksheet = async (submissionId) => {
    const res = await API.get(
      `/exams/${selectedExam.id}/submission/${submissionId}`
    );
    setSelectedSubmission(res.data);
  };

  /* ================= PUBLISH / LOCK ================= */

  const handlePublish = async () => {
    await API.put(`/exams/${selectedExam.id}/publish-result`);
    alert("Result Published Successfully");
    refreshExam();
  };

  const handleLock = async () => {
    await API.put(`/exams/${selectedExam.id}/lock-result`);
    alert("Result Locked Successfully");
    refreshExam();
  };

  const refreshExam = async () => {
    const res = await API.get("/exams");
    setExams(res.data);
    const updated = res.data.find(e => e.id === selectedExam.id);
    setSelectedExam(updated);
  };

  /* ================= RANK SYSTEM ================= */

  const rankedSubmissions = useMemo(() => {
    if (!submissions.length) return [];

    const sorted = [...submissions].sort(
      (a, b) => (b.total_marks || 0) - (a.total_marks || 0)
    );

    let rank = 1;

    return sorted.map((s, index) => {
      if (
        index > 0 &&
        s.total_marks < sorted[index - 1].total_marks
      ) {
        rank = index + 1;
      }

      return { ...s, rank };
    });
  }, [submissions]);

  /* ================= ANALYTICS ================= */

  const analytics = useMemo(() => {
    if (!submissions.length) return null;

    const total = submissions.length;
    const passCount = submissions.filter(s => s.percentage >= 35).length;
    const failCount = total - passCount;

    const marksArray = submissions.map(s => s.total_marks || 0);

    return {
      total,
      passCount,
      failCount,
      highest: Math.max(...marksArray),
      lowest: Math.min(...marksArray),
      average: (
        marksArray.reduce((a, b) => a + b, 0) / marksArray.length
      ).toFixed(2)
    };
  }, [submissions]);

  const filtered = rankedSubmissions.filter(s =>
    s.roll_number.toLowerCase().includes(search.toLowerCase())
  );

  const pieData = analytics
    ? [
        { name: "Pass", value: analytics.passCount },
        { name: "Fail", value: analytics.failCount }
      ]
    : [];

  const COLORS = ["#16a34a", "#dc2626"];

  return (
    <div style={wrapper}>
      <h2 style={title}>Results</h2>

      {/* ================= EXAM LIST ================= */}
      <div style={examGrid}>
        {exams.map((exam) => (
          <motion.div
            key={exam.id}
            whileHover={{ scale: 1.03 }}
            style={{
              ...examCard,
              border:
                selectedExam?.id === exam.id
                  ? `2px solid ${theme.colors.primary}`
                  : "none"
            }}
            onClick={() => loadExamResults(exam)}
          >
            <h4>{exam.title}</h4>
            <p>{exam.subject}</p>
            <p>Status: {exam.result_status}</p>
          </motion.div>
        ))}
      </div>

      {/* ================= PUBLISH / LOCK ================= */}
      {selectedExam && (
        <div style={{ marginBottom: "20px" }}>
          {selectedExam.result_status === "draft" && (
            <button style={publishBtn} onClick={handlePublish}>
              Publish Result
            </button>
          )}

          {selectedExam.result_status === "published" && (
            <button style={lockBtn} onClick={handleLock}>
              Lock Result
            </button>
          )}

          {selectedExam.result_status === "locked" && (
            <span style={{ color: "green", fontWeight: "bold" }}>
              🔒 Result Locked
            </span>
          )}
        </div>
      )}

      {/* ================= ANALYTICS ================= */}
      {selectedExam && analytics && (
        <>
          <div style={statsGrid}>
            <Stat label="Total" value={analytics.total} />
            <Stat label="Pass" value={analytics.passCount} />
            <Stat label="Fail" value={analytics.failCount} />
            <Stat label="Highest" value={analytics.highest} />
            <Stat label="Lowest" value={analytics.lowest} />
            <Stat label="Average" value={analytics.average} />
          </div>

          <div style={chartGrid}>
            <div style={chartCard}>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" outerRadius={90} label>
                    {pieData.map((entry, index) => (
                      <Cell key={index} fill={COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div style={chartCard}>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={rankedSubmissions}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="roll_number" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="total_marks" fill={theme.colors.primary} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ================= SEARCH ================= */}
          <input
            type="text"
            placeholder="Search Roll Number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={searchInput}
          />

          {/* ================= TABLE WITH RANK ================= */}
          <div style={tableCard}>
            <table style={tableStyle}>
              <thead style={theadStyle}>
                <tr>
                  <th style={th}>Rank</th>
                  <th style={th}>Roll No</th>
                  <th style={th}>Obtained</th>
                  <th style={th}>%</th>
                  <th style={th}>Grade</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
                  <tr
                    key={s.submission_id}
                    style={{
                      cursor: "pointer",
                      background:
                        s.rank === 1 ? "#fff9c4" : "white"
                    }}
                    onClick={() => loadMarksheet(s.submission_id)}
                  >
                    <td style={td}>{s.rank}</td>
                    <td style={td}>{s.roll_number}</td>
                    <td style={td}>{s.total_marks}</td>
                    <td style={td}>{s.percentage}%</td>
                    <td style={td}>{s.grade}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ================= MARKSHEET ================= */}
      {selectedSubmission && (
        <div style={marksheetWrapper}>
          <h3>Marksheet - Roll No {selectedSubmission.roll_number}</h3>

          <p>
            Total: {selectedSubmission.total_marks} /
            {selectedSubmission.max_marks}
          </p>
          <p>Percentage: {selectedSubmission.percentage}%</p>
          <p>Grade: {selectedSubmission.grade}</p>

          <div style={questionGrid}>
            {Object.entries(selectedSubmission.question_wise).map(
              ([qid, q]) => {
                const percent =
                  (q.final_marks / q.max_marks) * 100;

                return (
                  <div key={qid} style={questionCard}>
                    <h4>{qid}</h4>
                    <p>
                      {q.final_marks.toFixed(2)} / {q.max_marks}
                    </p>
                    <div style={progressContainer}>
                      <div
                        style={{
                          ...progressBar,
                          width: `${percent}%`
                        }}
                      />
                    </div>
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ================= SMALL COMPONENT ================= */

function Stat({ label, value }) {
  return (
    <div style={statCard}>
      <p>{label}</p>
      <h3>{value}</h3>
    </div>
  );
}

/* ================= STYLES ================= */

const wrapper = {
  maxWidth: "1200px",
  margin: "0 auto",
  padding: "20px"
};

const title = {
  marginBottom: "25px",
  color: theme.colors.primary
};

const examGrid = {
  display: "flex",
  gap: "15px",
  marginBottom: "30px",
  flexWrap: "wrap"
};

const examCard = {
  background: "white",
  padding: "15px",
  borderRadius: "10px",
  boxShadow: theme.shadow.soft,
  cursor: "pointer"
};

const statsGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
  gap: "15px",
  marginBottom: "20px"
};

const statCard = {
  background: "white",
  padding: "15px",
  borderRadius: "10px",
  boxShadow: theme.shadow.soft
};

const chartGrid = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "20px",
  marginBottom: "20px"
};

const chartCard = {
  background: "white",
  padding: "20px",
  borderRadius: "10px",
  boxShadow: theme.shadow.soft
};

const searchInput = {
  width: "100%",
  padding: "10px",
  marginBottom: "20px"
};

const tableCard = {
  background: "white",
  borderRadius: "10px",
  boxShadow: theme.shadow.soft,
  overflowX: "auto",
  marginBottom: "30px"
};

const tableStyle = { width: "100%", borderCollapse: "collapse" };
const theadStyle = { background: theme.colors.primary, color: "white" };
const th = { padding: "12px", textAlign: "center" };
const td = { padding: "12px", textAlign: "center" };

const publishBtn = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "none",
  background: theme.colors.primary,
  color: "white",
  cursor: "pointer"
};

const lockBtn = {
  padding: "8px 16px",
  borderRadius: "8px",
  border: "none",
  background: "#dc2626",
  color: "white",
  cursor: "pointer"
};

const marksheetWrapper = {
  background: "white",
  padding: "20px",
  borderRadius: "12px",
  boxShadow: theme.shadow.soft
};

const questionGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
  gap: "15px"
};

const questionCard = {
  background: "#f9f9f9",
  padding: "15px",
  borderRadius: "8px"
};

const progressContainer = {
  height: "6px",
  background: "#ddd",
  borderRadius: "4px",
  marginTop: "8px"
};

const progressBar = {
  height: "100%",
  background: theme.colors.primary
};