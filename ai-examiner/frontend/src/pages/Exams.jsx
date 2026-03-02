import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { theme } from "../theme/theme";
import API from "../services/api";
import { useNavigate } from "react-router-dom";

export default function Exams() {
  const navigate = useNavigate();

  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    title: "",
    class_name: "",
    division: "",
    subject: "",
    total_marks: ""
  });

  const fetchExams = async () => {
    try {
      const response = await API.get("/exams");
      setExams(response.data);
    } catch {
      setError("Failed to load exams");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();

    try {
      await API.post("/exams", {
        ...form,
        total_marks: Number(form.total_marks)
      });

      setForm({
        title: "",
        class_name: "",
        division: "",
        subject: "",
        total_marks: ""
      });

      fetchExams();
    } catch {
      setError("Failed to create exam");
    }
  };

  const handleDelete = async (id) => {
    try {
      await API.delete(`/exams/${id}`);
      fetchExams();
    } catch {
      setError("Failed to delete exam");
    }
  };

  return (
    <div style={pageWrapper}>
      <h2 style={pageTitle}>Exams</h2>

      {/* Create Exam Card */}
      <motion.form
        onSubmit={handleCreate}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        style={formCard}
      >
        <div style={formGrid}>
          {Object.keys(form).map((key) => (
            <input
              key={key}
              type={key === "total_marks" ? "number" : "text"}
              placeholder={key.replace("_", " ").toUpperCase()}
              value={form[key]}
              onChange={(e) =>
                setForm({ ...form, [key]: e.target.value })
              }
              style={inputStyle}
              required
            />
          ))}
        </div>

        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          type="submit"
          style={createButton}
        >
          Create Exam
        </motion.button>
      </motion.form>

      {error && (
        <p style={{ color: theme.colors.danger, marginBottom: "15px" }}>
          {error}
        </p>
      )}

      {loading ? (
        <p>Loading exams...</p>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={tableCard}
        >
          <table style={tableStyle}>
            <thead style={theadStyle}>
              <tr>
                <th style={thStyle}>Title</th>
                <th style={thStyle}>Class</th>
                <th style={thStyle}>Division</th>
                <th style={thStyle}>Subject</th>
                <th style={thStyle}>Total Marks</th>
                <th style={thStyle}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {exams.map((exam) => (
                <motion.tr
                  key={exam.id}
                  whileHover={{
                    backgroundColor: "#f9f5f2",
                    scale: 1.01
                  }}
                  onClick={() => navigate(`/exams/${exam.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <td style={tdStyle}>{exam.title}</td>
                  <td style={tdStyle}>{exam.class_name}</td>
                  <td style={tdStyle}>{exam.division}</td>
                  <td style={tdStyle}>{exam.subject}</td>
                  <td style={tdStyle}>{exam.total_marks}</td>
                  <td style={tdStyle}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation(); // IMPORTANT
                        handleDelete(exam.id);
                      }}
                      style={deleteButton}
                    >
                      Delete
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}
    </div>
  );
}

/* ---------------- STYLES ---------------- */

const pageWrapper = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "20px"
};

const pageTitle = {
  marginBottom: "25px",
  color: theme.colors.primary
};

const formCard = {
  background: "white",
  padding: "25px",
  borderRadius: theme.radius.lg,
  boxShadow: theme.shadow.soft,
  marginBottom: "30px",
  display: "flex",
  flexDirection: "column",
  gap: "20px"
};

const formGrid = {
  display: "grid",
  gridTemplateColumns: "repeat(5, 1fr)",
  gap: "15px"
};

const inputStyle = {
  padding: "10px",
  borderRadius: "8px",
  border: "1px solid #ddd",
  width: "100%"
};

const createButton = {
  padding: "12px",
  borderRadius: theme.radius.md,
  border: "none",
  background: theme.colors.primary,
  color: "white",
  cursor: "pointer"
};

const tableCard = {
  background: "white",
  borderRadius: theme.radius.lg,
  boxShadow: theme.shadow.soft,
  overflow: "hidden"
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse"
};

const theadStyle = {
  background: theme.colors.primary,
  color: "white"
};

const thStyle = {
  padding: "14px",
  textAlign: "center"
};

const tdStyle = {
  padding: "14px",
  textAlign: "center"
};

const deleteButton = {
  padding: "6px 12px",
  borderRadius: "8px",
  border: "none",
  background: theme.colors.danger,
  color: "white",
  cursor: "pointer"
};