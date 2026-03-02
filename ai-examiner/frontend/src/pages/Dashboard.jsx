import { useEffect, useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell
} from "recharts";

import API from "../services/api";
import { theme } from "../theme/theme";

export default function Dashboard() {
  const [exams, setExams] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [lastUpdated, setLastUpdated] = useState("");

  const fetchData = async () => {
    const examRes = await API.get("/exams");
    setExams(examRes.data);

    let all = [];
    for (let exam of examRes.data) {
      const res = await API.get(`/exams/${exam.id}/submissions`);
      all = [...all, ...res.data];
    }

    setSubmissions(all);
    setLastUpdated(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 20000);
    return () => clearInterval(interval);
  }, []);

  /* ================= KPI ================= */

  const totalExams = exams.length;
  const totalSubmissions = submissions.length;
  const evaluated = submissions.filter(s => s.total_marks !== null).length;
  const published = exams.filter(e => e.result_status === "published").length;

  /* ================= INSIGHT ================= */

  const avgScore =
    submissions.length > 0
      ? (
          submissions.reduce((a, b) => a + (b.total_marks || 0), 0) /
          submissions.length
        ).toFixed(2)
      : 0;

  const insight =
    avgScore >= 75
      ? "Excellent overall performance across exams."
      : avgScore >= 50
      ? "Moderate student performance. Improvement possible."
      : "Low overall performance. Review evaluation logic.";

  /* ================= CHART DATA ================= */

  const averagePerExam = useMemo(() => {
    return exams.map(exam => {
      const examSubs = submissions.filter(
        s => s.exam_id === exam.id && s.total_marks !== null
      );

      const avg =
        examSubs.length > 0
          ? examSubs.reduce((a, b) => a + b.total_marks, 0) /
            examSubs.length
          : 0;

      return {
        name: exam.title,
        average: Number(avg.toFixed(2))
      };
    });
  }, [exams, submissions]);

  const statusData = [
    { name: "Draft", value: exams.filter(e => e.result_status === "draft").length },
    { name: "Published", value: exams.filter(e => e.result_status === "published").length },
    { name: "Locked", value: exams.filter(e => e.result_status === "locked").length }
  ];

  const COLORS = ["#94a3b8", "#f59e0b", "#22c55e"];

  return (
    <div style={wrapper}>
      <div style={header}>
        <div>
          <h2 style={title}>AI Examiner Control Center</h2>
          <p style={subtitle}>
            System overview • Last updated {lastUpdated}
          </p>
        </div>
      </div>

      {/* KPI */}
      <div style={kpiGrid}>
        <KPI label="Total Exams" value={totalExams} />
        <KPI label="Total Submissions" value={totalSubmissions} />
        <KPI label="Evaluated Papers" value={evaluated} />
        <KPI label="Published Results" value={published} />
      </div>

      {/* Insight Panel */}
      <div style={insightCard}>
        <h4>AI Performance Insight</h4>
        <p>
          Average Score: <strong>{avgScore}</strong>
        </p>
        <p style={{ marginTop: 8 }}>{insight}</p>
      </div>

      {/* Charts */}
      <div style={chartGrid}>
        <div style={chartCard}>
          <h4>Average Marks Per Exam</h4>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={averagePerExam}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="average" fill={theme.colors.primary} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={chartCard}>
          <h4>Exam Status Distribution</h4>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={statusData} dataKey="value" outerRadius={95} label>
                {statusData.map((entry, index) => (
                  <Cell key={index} fill={COLORS[index]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

/* ================= COMPONENTS ================= */

function KPI({ label, value }) {
  return (
    <motion.div whileHover={{ y: -5 }} style={kpiCard}>
      <div style={kpiValue}>{value}</div>
      <div style={kpiLabel}>{label}</div>
    </motion.div>
  );
}

/* ================= STYLES ================= */

const wrapper = {
  maxWidth: "1200px",
  margin: "0 auto",
  padding: "50px 30px"
};

const header = {
  marginBottom: "40px"
};

const title = {
  fontSize: "30px",
  fontWeight: "700",
  color: theme.colors.primary
};

const subtitle = {
  color: "#64748b",
  marginTop: "6px"
};

const kpiGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "25px",
  marginBottom: "40px"
};

const kpiCard = {
  background: "white",
  padding: "30px",
  borderRadius: "18px",
  boxShadow: "0 20px 40px rgba(0,0,0,0.05)",
  textAlign: "center"
};

const kpiValue = {
  fontSize: "34px",
  fontWeight: "700"
};

const kpiLabel = {
  marginTop: "8px",
  color: "#64748b"
};

const insightCard = {
  background: "#f8fafc",
  padding: "25px",
  borderRadius: "18px",
  marginBottom: "40px",
  boxShadow: "0 10px 30px rgba(0,0,0,0.05)"
};

const chartGrid = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "30px"
};

const chartCard = {
  background: "white",
  padding: "25px",
  borderRadius: "18px",
  boxShadow: "0 20px 40px rgba(0,0,0,0.05)"
};