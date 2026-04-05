import { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  Tooltip, CartesianGrid, PieChart, Pie, Cell, LineChart,
  Line, Area, AreaChart
} from "recharts";
import API from "../services/api";
import { theme } from "../theme/theme";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }
});

const GRADE_COLORS = {
  "First Class with Distinction": "#10b981",
  "Distinction":                  "#059669",
  "First Class":                  "#3b82f6",
  "Second Class":                 "#f59e0b",
  "Pass":                         "#8b5cf6",
  "Fail":                         "#ef4444",
};

const STATUS_COLORS  = ["#94a3b8", "#f59e0b", "#10b981"];
const BAR_GRADIENT   = ["#6366f1", "#8b5cf6"];

export default function Dashboard() {
  const [exams, setExams]           = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [lastUpdated, setLastUpdated] = useState("");
  const [activeTab, setActiveTab]   = useState("overview");

  const fetchData = async () => {
    const examRes = await API.get("/exams");
    setExams(examRes.data);
    let all = [];
    for (let exam of examRes.data) {
      const res = await API.get(`/exams/${exam.id}/submissions`);
      all = [...all, ...res.data.map(s => ({ ...s, exam_title: exam.title, subject: exam.subject }))];
    }
    setSubmissions(all);
    setLastUpdated(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 20000);
    return () => clearInterval(interval);
  }, []);

  const totalExams       = exams.length;
  const totalSubmissions = submissions.length;
  const evaluated        = submissions.filter(s => s.total_marks !== null).length;
  const published        = exams.filter(e => e.result_status === "published").length;
  const locked           = exams.filter(e => e.result_status === "locked").length;
  const passRate         = evaluated > 0
    ? Math.round(submissions.filter(s => s.grade && s.grade !== "Fail").length / evaluated * 100)
    : 0;

  const avgScore = submissions.length > 0
    ? (submissions.reduce((a, b) => a + (b.total_marks || 0), 0) / submissions.length).toFixed(1)
    : 0;

  const avgPercent = submissions.length > 0
    ? (submissions.reduce((a, b) => a + (b.percentage || 0), 0) / submissions.length).toFixed(1)
    : 0;

  const averagePerExam = useMemo(() => exams.map(exam => {
    const subs = submissions.filter(s => s.exam_id === exam.id && s.total_marks !== null);
    const avg  = subs.length > 0
      ? subs.reduce((a, b) => a + b.total_marks, 0) / subs.length : 0;
    return { name: exam.title.length > 12 ? exam.title.slice(0, 12) + "…" : exam.title, average: +avg.toFixed(1), count: subs.length };
  }), [exams, submissions]);

  const gradeData = useMemo(() => {
    const counts = {};
    submissions.forEach(s => { if (s.grade) counts[s.grade] = (counts[s.grade] || 0) + 1; });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [submissions]);

  const statusData = [
    { name: "Draft",     value: exams.filter(e => e.result_status === "draft").length },
    { name: "Published", value: exams.filter(e => e.result_status === "published").length },
    { name: "Locked",    value: exams.filter(e => e.result_status === "locked").length },
  ];

  const recentSubmissions = [...submissions]
    .filter(s => s.total_marks !== null)
    .slice(-8)
    .map((s, i) => ({ name: `#${i + 1}`, percentage: s.percentage || 0 }));

  const topPerformers = [...submissions]
    .filter(s => s.percentage != null)
    .sort((a, b) => b.percentage - a.percentage)
    .slice(0, 5);

  const insightColor = avgPercent >= 75 ? "#10b981" : avgPercent >= 50 ? "#f59e0b" : "#ef4444";
  const insightText  = avgPercent >= 75
    ? "Excellent performance across all exams"
    : avgPercent >= 50
    ? "Moderate performance — improvement possible"
    : "Low performance — review evaluation";

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload?.length) {
      return (
        <div style={tooltipStyle}>
          <div style={{ fontWeight: 600, marginBottom: 4, color: "#1e293b" }}>{label}</div>
          {payload.map((p, i) => (
            <div key={i} style={{ color: p.color, fontSize: 13 }}>{p.name}: {p.value}</div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={wrapper}>

      {/* ── Header ── */}
      <motion.div style={headerRow} {...fadeUp(0)}>
        <div>
          <h1 style={mainTitle}>Control Center</h1>
          <p style={subText}>AI Examiner · Updated {lastUpdated || "—"}</p>
        </div>
        <div style={headerRight}>
          <div style={{ ...liveChip, background: evaluated > 0 ? "#dcfce7" : "#f1f5f9" }}>
            <span style={{ ...liveDot, background: evaluated > 0 ? "#16a34a" : "#94a3b8" }} />
            <span style={{ color: evaluated > 0 ? "#16a34a" : "#64748b", fontSize: 12, fontWeight: 600 }}>
              {evaluated > 0 ? "System Active" : "No Data Yet"}
            </span>
          </div>
        </div>
      </motion.div>

      {/* ── KPI Grid ── */}
      <div style={kpiGrid}>
        {[
          { label: "Total Exams",     value: totalExams,       icon: "📋", color: "#6366f1", bg: "#eef2ff" },
          { label: "Submissions",     value: totalSubmissions, icon: "📄", color: "#0ea5e9", bg: "#e0f2fe" },
          { label: "Evaluated",       value: evaluated,        icon: "✅", color: "#10b981", bg: "#dcfce7" },
          { label: "Avg Score",       value: `${avgPercent}%`, icon: "📊", color: "#f59e0b", bg: "#fef9c3" },
          { label: "Pass Rate",       value: `${passRate}%`,   icon: "🎯", color: "#8b5cf6", bg: "#ede9fe" },
          { label: "Published",       value: published,        icon: "🔓", color: "#06b6d4", bg: "#cffafe" },
        ].map((kpi, i) => (
          <motion.div key={kpi.label} style={kpiCard} whileHover={{ y: -4, boxShadow: "0 20px 40px rgba(0,0,0,0.1)" }} {...fadeUp(i * 0.07)}>
            <div style={{ ...kpiIcon, background: kpi.bg, color: kpi.color }}>{kpi.icon}</div>
            <div style={{ ...kpiValue, color: kpi.color }}>{kpi.value}</div>
            <div style={kpiLabel}>{kpi.label}</div>
          </motion.div>
        ))}
      </div>

      {/* ── Insight Banner ── */}
      <motion.div style={{ ...insightBanner, borderLeft: `4px solid ${insightColor}` }} {...fadeUp(0.3)}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 20 }}>{avgPercent >= 75 ? "🏆" : avgPercent >= 50 ? "📈" : "⚠️"}</span>
          <div>
            <div style={{ fontWeight: 700, color: insightColor, fontSize: 14 }}>{insightText}</div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
              Average score: {avgScore} marks · {avgPercent}% · {evaluated} papers evaluated
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── Tab nav ── */}
      <motion.div style={tabRow} {...fadeUp(0.35)}>
        {["overview", "grades", "exams"].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            ...tabBtn,
            background: activeTab === tab ? theme.colors.primary : "white",
            color:      activeTab === tab ? "white" : "#64748b",
            boxShadow:  activeTab === tab ? "0 4px 12px rgba(99,102,241,0.3)" : "none",
          }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </motion.div>

      <AnimatePresence mode="wait">

        {/* ── Overview Tab ── */}
        {activeTab === "overview" && (
          <motion.div key="overview"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }} transition={{ duration: 0.3 }}
          >
            <div style={chartGrid}>

              {/* Bar chart */}
              <div style={chartCard}>
                <div style={chartTitle}>Average Marks Per Exam</div>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={averagePerExam} barSize={32}>
                    <defs>
                      <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%"   stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#8b5cf6" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="average" fill="url(#barGrad)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Area chart */}
              <div style={chartCard}>
                <div style={chartTitle}>Recent Submission Scores</div>
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={recentSubmissions}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"   stopColor="#6366f1" stopOpacity={0.2} />
                        <stop offset="95%"  stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area type="monotone" dataKey="percentage" stroke="#6366f1" strokeWidth={2.5} fill="url(#areaGrad)" dot={{ fill: "#6366f1", r: 4 }} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Pie chart */}
              <div style={chartCard}>
                <div style={chartTitle}>Exam Status Distribution</div>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={statusData} dataKey="value" outerRadius={90} innerRadius={50} paddingAngle={3} label={({ name, value }) => `${name}: ${value}`} labelLine={false}>
                      {statusData.map((_, i) => (
                        <Cell key={i} fill={STATUS_COLORS[i]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={legendRow}>
                  {statusData.map((s, i) => (
                    <div key={s.name} style={legendItem}>
                      <div style={{ ...legendDot, background: STATUS_COLORS[i] }} />
                      <span>{s.name} ({s.value})</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top performers */}
              <div style={chartCard}>
                <div style={chartTitle}>Top Performers</div>
                {topPerformers.length === 0 ? (
                  <div style={emptyState}>No evaluated submissions yet</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
                    {topPerformers.map((s, i) => (
                      <div key={i} style={performerRow}>
                        <div style={{ ...rankBadge, background: i === 0 ? "#fef9c3" : i === 1 ? "#f1f5f9" : "#fef3c7" }}>
                          {i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i + 1}`}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: 13, color: "#1e293b" }}>Roll {s.roll_number}</div>
                          <div style={{ fontSize: 11, color: "#94a3b8" }}>{s.exam_title || "—"}</div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontWeight: 700, fontSize: 14, color: "#6366f1" }}>{s.percentage}%</div>
                          <div style={{ fontSize: 11, color: GRADE_COLORS[s.grade] || "#64748b" }}>{s.grade}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {/* ── Grades Tab ── */}
        {activeTab === "grades" && (
          <motion.div key="grades"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }} transition={{ duration: 0.3 }}
          >
            <div style={chartGrid}>
              <div style={{ ...chartCard, gridColumn: "span 2" }}>
                <div style={chartTitle}>Grade Distribution</div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={gradeData} barSize={40}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {gradeData.map((entry, i) => (
                        <Cell key={i} fill={GRADE_COLORS[entry.name] || "#94a3b8"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div style={{ ...chartCard, gridColumn: "span 2" }}>
                <div style={chartTitle}>All Submissions</div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: "#f8fafc" }}>
                        {["Roll No", "Subject", "Marks", "%", "Grade"].map(h => (
                          <th key={h} style={tableHead}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.filter(s => s.total_marks != null).slice(0, 20).map((s, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={tableCell}>{s.roll_number}</td>
                          <td style={tableCell}>{s.subject || "—"}</td>
                          <td style={tableCell}>{s.total_marks}</td>
                          <td style={tableCell}>{s.percentage}%</td>
                          <td style={tableCell}>
                            <span style={{ ...gradePill, background: `${GRADE_COLORS[s.grade]}22`, color: GRADE_COLORS[s.grade] || "#64748b" }}>
                              {s.grade || "—"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── Exams Tab ── */}
        {activeTab === "exams" && (
          <motion.div key="exams"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }} transition={{ duration: 0.3 }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {exams.length === 0 ? (
                <div style={{ ...chartCard, textAlign: "center", color: "#94a3b8", padding: 40 }}>No exams created yet</div>
              ) : (
                exams.map((exam, i) => {
                  const subs    = submissions.filter(s => s.exam_id === exam.id && s.total_marks != null);
                  const avgPct  = subs.length > 0
                    ? (subs.reduce((a, b) => a + (b.percentage || 0), 0) / subs.length).toFixed(1) : null;
                  const statusC = exam.result_status === "locked" ? "#10b981" : exam.result_status === "published" ? "#f59e0b" : "#94a3b8";
                  return (
                    <motion.div key={exam.id} style={examRow} whileHover={{ x: 4 }} {...fadeUp(i * 0.05)}>
                      <div style={{ ...examIdBox, color: theme.colors.primary }}>#{exam.id}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 14, color: "#1e293b" }}>{exam.title}</div>
                        <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
                          {exam.subject} · {exam.class_name} · Div {exam.division} · {exam.total_marks} marks
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                        <div style={{ textAlign: "center" }}>
                          <div style={{ fontWeight: 700, fontSize: 16, color: "#6366f1" }}>{subs.length}</div>
                          <div style={{ fontSize: 11, color: "#94a3b8" }}>submissions</div>
                        </div>
                        {avgPct && (
                          <div style={{ textAlign: "center" }}>
                            <div style={{ fontWeight: 700, fontSize: 16, color: "#10b981" }}>{avgPct}%</div>
                            <div style={{ fontSize: 11, color: "#94a3b8" }}>avg score</div>
                          </div>
                        )}
                        <span style={{ ...statusChip, background: `${statusC}22`, color: statusC }}>
                          {exam.result_status}
                        </span>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}

/* ── STYLES ── */
const wrapper      = { maxWidth: "1200px", margin: "0 auto", padding: "32px 24px", fontFamily: "'Segoe UI', system-ui, sans-serif" };
const headerRow    = { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 };
const mainTitle    = { fontSize: 28, fontWeight: 800, color: "#0f172a", margin: 0, letterSpacing: "-0.5px" };
const subText      = { fontSize: 13, color: "#94a3b8", marginTop: 4 };
const headerRight  = { display: "flex", alignItems: "center", gap: 12 };
const liveChip     = { display: "flex", alignItems: "center", gap: 6, padding: "6px 14px", borderRadius: 20, border: "1px solid #e2e8f0" };
const liveDot      = { width: 8, height: 8, borderRadius: "50%", animation: "pulse 2s infinite" };

const kpiGrid = { display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 14, marginBottom: 20 };
const kpiCard = { background: "white", padding: "20px 16px", borderRadius: 16, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", textAlign: "center", cursor: "default", transition: "all 0.2s" };
const kpiIcon  = { width: 40, height: 40, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 10px", fontSize: 18 };
const kpiValue = { fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px" };
const kpiLabel = { fontSize: 11, color: "#94a3b8", marginTop: 4, fontWeight: 500 };

const insightBanner = { background: "white", padding: "14px 20px", borderRadius: 14, boxShadow: "0 2px 12px rgba(0,0,0,0.05)", marginBottom: 24 };

const tabRow = { display: "flex", gap: 8, marginBottom: 20 };
const tabBtn  = { padding: "8px 20px", borderRadius: 20, border: "1px solid #e2e8f0", fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.2s" };

const chartGrid = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 };
const chartCard = { background: "white", padding: "20px 24px", borderRadius: 16, boxShadow: "0 2px 12px rgba(0,0,0,0.06)" };
const chartTitle = { fontSize: 14, fontWeight: 700, color: "#0f172a", marginBottom: 16 };

const legendRow  = { display: "flex", gap: 16, justifyContent: "center", marginTop: 12 };
const legendItem = { display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748b" };
const legendDot  = { width: 8, height: 8, borderRadius: "50%" };

const tooltipStyle = { background: "white", border: "1px solid #e2e8f0", borderRadius: 10, padding: "10px 14px", boxShadow: "0 4px 16px rgba(0,0,0,0.1)", fontSize: 13 };

const performerRow = { display: "flex", alignItems: "center", gap: 12, padding: "10px 12px", borderRadius: 10, background: "#f8fafc" };
const rankBadge    = { width: 32, height: 32, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700 };

const tableHead = { padding: "10px 14px", textAlign: "left", fontWeight: 600, fontSize: 12, color: "#64748b", borderBottom: "1px solid #e2e8f0" };
const tableCell = { padding: "10px 14px", color: "#334155" };
const gradePill = { padding: "2px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600 };
const emptyState = { textAlign: "center", color: "#94a3b8", padding: "40px 0", fontSize: 13 };

const examRow   = { background: "white", padding: "16px 20px", borderRadius: 14, boxShadow: "0 2px 12px rgba(0,0,0,0.06)", display: "flex", alignItems: "center", gap: 16, cursor: "default" };
const examIdBox = { width: 44, height: 44, borderRadius: 10, background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 13, flexShrink: 0 };
const statusChip = { padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 700 };