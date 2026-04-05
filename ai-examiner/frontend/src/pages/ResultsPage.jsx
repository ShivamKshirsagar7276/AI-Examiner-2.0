import { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from "recharts";
import API from "../services/api";
import { theme } from "../theme/theme";

export default function ResultsPage() {
  const [exams, setExams]                           = useState([]);
  const [selectedExam, setSelectedExam]             = useState(null);
  const [submissions, setSubmissions]               = useState([]);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [search, setSearch]                         = useState("");
  const [reasoning, setReasoning]                   = useState(null);
  const [reasoningLoading, setReasoningLoading]     = useState(false);
  const [showReasoning, setShowReasoning]           = useState(false);
  const [generatingMsg, setGeneratingMsg]           = useState("");

  useEffect(() => {
    const fetchExams = async () => {
      const res = await API.get("/exams");
      setExams(res.data);
    };
    fetchExams();
  }, []);

  const loadExamResults = async (exam) => {
    setSelectedExam(exam);
    setSelectedSubmission(null);
    setReasoning(null);
    setShowReasoning(false);
    const res = await API.get(`/exams/${exam.id}/submissions`);
    setSubmissions(res.data);
  };

  const loadMarksheet = async (submissionId) => {
    const res = await API.get(`/exams/${selectedExam.id}/submission/${submissionId}`);
    setSelectedSubmission(res.data);
    setReasoning(null);
    setShowReasoning(false);
  };

  const loadReasoning = async () => {
    if (!selectedSubmission) return;
    setReasoningLoading(true);
    setShowReasoning(true);
    setGeneratingMsg("Generating AI reasoning for each question... this may take a moment.");

    try {
      await API.post(
        `/exams/${selectedExam.id}/submission/${selectedSubmission.submission_id}/generate-reasoning`
      );

      setGeneratingMsg("Fetching results...");

      const res = await API.get(
        `/results/faculty/${selectedSubmission.submission_id}/reasoning`
      );
      setReasoning(res.data);
    } catch (err) {
      alert("Failed to generate AI reasoning. Please try again.");
      setShowReasoning(false);
    } finally {
      setReasoningLoading(false);
      setGeneratingMsg("");
    }
  };

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
    const res     = await API.get("/exams");
    setExams(res.data);
    const updated = res.data.find(e => e.id === selectedExam.id);
    setSelectedExam(updated);
  };

  const rankedSubmissions = useMemo(() => {
    if (!submissions.length) return [];
    const sorted = [...submissions].sort((a, b) => (b.total_marks || 0) - (a.total_marks || 0));
    let rank = 1;
    return sorted.map((s, index) => {
      if (index > 0 && s.total_marks < sorted[index - 1].total_marks) rank = index + 1;
      return { ...s, rank };
    });
  }, [submissions]);

  const analytics = useMemo(() => {
    if (!submissions.length) return null;
    const total      = submissions.length;
    const passCount  = submissions.filter(s => s.percentage >= 35).length;
    const failCount  = total - passCount;
    const marksArray = submissions.map(s => s.total_marks || 0);
    return {
      total, passCount, failCount,
      highest: Math.max(...marksArray),
      lowest:  Math.min(...marksArray),
      average: (marksArray.reduce((a, b) => a + b, 0) / marksArray.length).toFixed(2)
    };
  }, [submissions]);

  const filtered = rankedSubmissions.filter(s =>
    s.roll_number.toLowerCase().includes(search.toLowerCase())
  );

  const pieData = analytics
    ? [{ name: "Pass", value: analytics.passCount }, { name: "Fail", value: analytics.failCount }]
    : [];
  const COLORS = ["#16a34a", "#dc2626"];

  return (
    <div style={wrapper}>
      <h2 style={title}>Results</h2>

      {/* EXAM LIST */}
      <div style={examGrid}>
        {exams.map((exam) => (
          <motion.div
            key={exam.id}
            whileHover={{ scale: 1.03 }}
            style={{
              ...examCard,
              border: selectedExam?.id === exam.id ? `2px solid ${theme.colors.primary}` : "none"
            }}
            onClick={() => loadExamResults(exam)}
          >
            <h4>{exam.title}</h4>
            <p>{exam.subject}</p>
            <p>Status: {exam.result_status}</p>
          </motion.div>
        ))}
      </div>

      {/* PUBLISH / LOCK */}
      {selectedExam && (
        <div style={{ marginBottom: "20px" }}>
          {selectedExam.result_status === "draft" && (
            <button style={publishBtn} onClick={handlePublish}>Publish Result</button>
          )}
          {selectedExam.result_status === "published" && (
            <button style={lockBtn} onClick={handleLock}>Lock Result</button>
          )}
          {selectedExam.result_status === "locked" && (
            <span style={{ color: "green", fontWeight: "bold" }}>🔒 Result Locked</span>
          )}
        </div>
      )}

      {/* ANALYTICS */}
      {selectedExam && analytics && (
        <>
          <div style={statsGrid}>
            <Stat label="Total"   value={analytics.total} />
            <Stat label="Pass"    value={analytics.passCount} />
            <Stat label="Fail"    value={analytics.failCount} />
            <Stat label="Highest" value={analytics.highest} />
            <Stat label="Lowest"  value={analytics.lowest} />
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

          <input
            type="text"
            placeholder="Search Roll Number..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={searchInput}
          />

          {/* TABLE */}
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
                    style={{ cursor: "pointer", background: s.rank === 1 ? "#fff9c4" : "white" }}
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

      {/* MARKSHEET */}
      {selectedSubmission && (
        <div style={marksheetWrapper}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
            <h3 style={{ margin: 0, color: theme.colors.primary }}>
              Marksheet — Roll No {selectedSubmission.roll_number}
            </h3>
            <button onClick={loadReasoning} style={reasoningBtn}>
              🤖 View AI Reasoning
            </button>
          </div>

          <div style={marksheetMeta}>
            <span>Total: <strong>{selectedSubmission.total_marks} / {selectedSubmission.max_marks}</strong></span>
            <span>Percentage: <strong>{selectedSubmission.percentage}%</strong></span>
            <span>Grade: <strong>{selectedSubmission.grade}</strong></span>
          </div>

          <div style={questionGrid}>
            {Object.entries(selectedSubmission.question_wise).map(([qid, q]) => {
              const percent = (q.final_marks / q.max_marks) * 100;
              return (
                <div key={qid} style={questionCard}>
                  <h4 style={{ margin: "0 0 6px 0", color: theme.colors.primary }}>{qid}</h4>
                  <p style={{ margin: "0 0 8px 0", fontSize: "14px", fontWeight: "600" }}>
                    {q.final_marks?.toFixed(2)} / {q.max_marks}
                  </p>
                  <div style={progressContainer}>
                    <div style={{
                      ...progressBar,
                      width: `${percent}%`,
                      background: percent >= 70 ? "#16a34a" : percent >= 40 ? "#d97706" : "#dc2626"
                    }} />
                  </div>
                  {q.ignored_due_to_best_of && (
                    <div style={{ fontSize: "10px", color: "#888", marginTop: "6px" }}>
                      ⚠ Not counted (best-of)
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AI REASONING PANEL */}
      {showReasoning && (
        <div style={reasoningWrapper}>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
            <h3 style={{ margin: 0, color: theme.colors.primary }}>
              🤖 AI Evaluation Reasoning
            </h3>
            <button onClick={() => setShowReasoning(false)} style={closeBtn}>✕ Close</button>
          </div>

          {reasoningLoading ? (
            <div style={{ textAlign: "center", padding: "40px", color: "#888" }}>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1 }}
                style={{ ...spinner, margin: "0 auto 12px" }}
              />
              <div style={{ marginBottom: "8px", fontWeight: "600" }}>
                Generating AI reasoning...
              </div>
              <div style={{ fontSize: "13px", color: "#aaa" }}>
                {generatingMsg}
              </div>
            </div>
          ) : reasoning ? (
            <>
              {/* Summary */}
              <div style={reasoningSummary}>
                <div style={summaryItem}>
                  <span style={summaryLabel}>Total Marks</span>
                  <span style={summaryValue}>{reasoning.total_marks} / {reasoning.max_marks}</span>
                </div>
                <div style={summaryItem}>
                  <span style={summaryLabel}>Marks Cut</span>
                  <span style={{ ...summaryValue, color: "#dc2626" }}>-{reasoning.marks_cut}</span>
                </div>
                <div style={summaryItem}>
                  <span style={summaryLabel}>Percentage</span>
                  <span style={summaryValue}>{reasoning.percentage}%</span>
                </div>
                <div style={summaryItem}>
                  <span style={summaryLabel}>Grade</span>
                  <span style={{ ...summaryValue, color: theme.colors.primary }}>{reasoning.grade}</span>
                </div>
              </div>

              {/* Per Question */}
              {reasoning.questions.map((q) => (
                <div key={q.question_id} style={questionReasoningCard}>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                    <h4 style={{ margin: 0, color: theme.colors.primary, fontSize: "16px" }}>
                      {q.question_id}
                    </h4>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <span style={{ fontSize: "12px", color: "#888" }}>
                        Confidence: {q.confidence}%
                      </span>
                      <span style={{
                        fontWeight: "700",
                        fontSize: "16px",
                        color: q.final_marks === q.max_marks ? "#16a34a"
                          : q.final_marks >= q.max_marks * 0.5 ? "#d97706"
                          : "#dc2626"
                      }}>
                        {q.final_marks} / {q.max_marks}
                      </span>
                      {q.marks_cut > 0 && (
                        <span style={{ fontSize: "12px", color: "#dc2626", fontWeight: "600" }}>
                          -{q.marks_cut} cut
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Score Bars */}
                  <div style={scoreBarsGrid}>
                    {[
                      { label: "Semantic", value: q.semantic_score },
                      { label: "Coverage", value: q.coverage_score },
                      { label: "Quality",  value: q.quality_score },
                      { label: "Diagram",  value: q.diagram_score }
                    ].map((s) => (
                      <div key={s.label} style={scoreBarItem}>
                        <div style={{ fontSize: "11px", color: "#888", marginBottom: "4px" }}>{s.label}</div>
                        <div style={{ fontSize: "13px", fontWeight: "600", color: "#333", marginBottom: "4px" }}>
                          {Math.round(s.value * 100)}%
                        </div>
                        <div style={miniTrack}>
                          <div style={{
                            ...miniFill,
                            width: `${s.value * 100}%`,
                            background: s.value >= 0.7 ? "#16a34a" : s.value >= 0.4 ? "#d97706" : "#dc2626"
                          }} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Component Reasoning */}
                  {q.components && q.components.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
                      {q.components.map((c, i) => (
                        <div key={i} style={componentRow}>
                          <span style={{
                            fontSize: "18px",
                            lineHeight: "1.4",
                            minWidth: "22px",
                            color: c.status === "✔" ? "#16a34a" : "#dc2626"
                          }}>
                            {c.status}
                          </span>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: "600", fontSize: "13px", color: "#333" }}>
                              {c.component}
                            </div>
                            <div style={{ fontSize: "12px", color: "#666", marginTop: "3px", lineHeight: "1.6" }}>
                              {c.reasoning}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={noReasoningBox}>
                      ⚠ Reasoning could not be generated for this question.
                    </div>
                  )}

                  {/* Overall Feedback */}
                  {q.overall_feedback ? (
                    <div style={feedbackBox}>
                      <div style={{ fontSize: "11px", fontWeight: "700", color: theme.colors.primary, marginBottom: "5px" }}>
                        📋 Examiner Feedback
                      </div>
                      <div style={{ fontSize: "12px", color: "#444", lineHeight: "1.6" }}>
                        {q.overall_feedback}
                      </div>
                    </div>
                  ) : null}

                  {q.ignored_due_to_best_of && (
                    <div style={ignoredBadge}>
                      ⚠ This question was not counted (best-of selection applied)
                    </div>
                  )}

                </div>
              ))}
            </>
          ) : null}
        </div>
      )}

    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div style={statCard}>
      <p style={{ margin: "0 0 4px 0", color: "#888", fontSize: "12px" }}>{label}</p>
      <h3 style={{ margin: 0, color: theme.colors.primary }}>{value}</h3>
    </div>
  );
}

/* ================= STYLES ================= */

const wrapper      = { maxWidth: "1200px", margin: "0 auto", padding: "20px" };
const title        = { marginBottom: "25px", color: theme.colors.primary };
const examGrid     = { display: "flex", gap: "15px", marginBottom: "30px", flexWrap: "wrap" };
const examCard     = { background: "white", padding: "15px", borderRadius: "10px", boxShadow: theme.shadow.soft, cursor: "pointer" };
const statsGrid    = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "15px", marginBottom: "20px" };
const statCard     = { background: "white", padding: "15px", borderRadius: "10px", boxShadow: theme.shadow.soft };
const chartGrid    = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "20px" };
const chartCard    = { background: "white", padding: "20px", borderRadius: "10px", boxShadow: theme.shadow.soft };
const searchInput  = { width: "100%", padding: "10px", marginBottom: "20px" };
const tableCard    = { background: "white", borderRadius: "10px", boxShadow: theme.shadow.soft, overflowX: "auto", marginBottom: "30px" };
const tableStyle   = { width: "100%", borderCollapse: "collapse" };
const theadStyle   = { background: theme.colors.primary, color: "white" };
const th           = { padding: "12px", textAlign: "center" };
const td           = { padding: "12px", textAlign: "center" };
const publishBtn   = { padding: "8px 16px", borderRadius: "8px", border: "none", background: theme.colors.primary, color: "white", cursor: "pointer" };
const lockBtn      = { padding: "8px 16px", borderRadius: "8px", border: "none", background: "#dc2626", color: "white", cursor: "pointer" };
const marksheetWrapper  = { background: "white", padding: "20px", borderRadius: "12px", boxShadow: theme.shadow.soft, marginBottom: "20px" };
const marksheetMeta     = { display: "flex", gap: "24px", fontSize: "14px", color: "#555", marginBottom: "16px" };
const questionGrid      = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "15px" };
const questionCard      = { background: "#f9f9f9", padding: "15px", borderRadius: "8px" };
const progressContainer = { height: "6px", background: "#ddd", borderRadius: "4px", marginTop: "8px" };
const progressBar       = { height: "100%", borderRadius: "4px" };
const reasoningBtn  = { padding: "8px 18px", borderRadius: "8px", border: "none", background: theme.colors.primary, color: "white", cursor: "pointer", fontSize: "13px", fontWeight: "600" };
const closeBtn      = { padding: "6px 14px", borderRadius: "8px", border: "1px solid #ddd", background: "white", cursor: "pointer", fontSize: "13px" };
const reasoningWrapper = { background: "white", padding: "24px", borderRadius: "14px", boxShadow: theme.shadow.soft, marginBottom: "20px" };
const reasoningSummary = { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "24px", background: "#f8f9fa", padding: "16px", borderRadius: "10px" };
const summaryItem      = { display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" };
const summaryLabel     = { fontSize: "11px", color: "#888", fontWeight: "500" };
const summaryValue     = { fontSize: "20px", fontWeight: "700", color: "#333" };
const questionReasoningCard = { border: "1px solid #eee", borderRadius: "12px", padding: "16px", marginBottom: "16px" };
const scoreBarsGrid         = { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginBottom: "14px", background: "#f8f9fa", padding: "12px", borderRadius: "8px" };
const scoreBarItem          = { display: "flex", flexDirection: "column" };
const miniTrack             = { height: "6px", background: "#e5e7eb", borderRadius: "99px", overflow: "hidden" };
const miniFill              = { height: "100%", borderRadius: "99px" };
const componentRow   = { display: "flex", gap: "10px", alignItems: "flex-start", padding: "8px 10px", background: "#fafafa", borderRadius: "8px" };
const noReasoningBox = { background: "#fff9e6", border: "1px solid #fde68a", borderRadius: "8px", padding: "12px", fontSize: "12px", color: "#92400e", marginBottom: "12px" };
const feedbackBox    = { background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "8px", padding: "12px" };
const ignoredBadge   = { background: "#fef9c3", border: "1px solid #fde047", borderRadius: "6px", padding: "8px 12px", fontSize: "12px", color: "#854d0e", marginTop: "8px" };
const spinner        = { width: "24px", height: "24px", border: "3px solid #eee", borderTop: `3px solid ${theme.colors.primary}`, borderRadius: "50%" };