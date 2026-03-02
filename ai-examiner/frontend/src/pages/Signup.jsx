import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { theme } from "../theme/theme";
import API from "../services/api";
import { FiEye, FiEyeOff } from "react-icons/fi";

export default function Signup() {
  const navigate = useNavigate();
  const cardRef = useRef();

  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleMouseMove = (e) => {
    const card = cardRef.current;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rotateX = -(y - rect.height / 2) / 20;
    const rotateY = (x - rect.width / 2) / 20;
    card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  };

  const resetTilt = () => {
    cardRef.current.style.transform = "rotateX(0) rotateY(0)";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.email.includes("@")) {
      return setError("Enter a valid email address");
    }

    if (form.password.length < 6) {
      return setError("Password must be at least 6 characters");
    }

    try {
      setLoading(true);
      setError("");

      await API.post("/auth/signup", form);

      setSuccess(true);

      setTimeout(() => navigate("/login"), 1500);

    } catch (err) {
      setError(err.response?.data?.detail || "Signup failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={containerStyle}>

      {/* Soft Glow Background */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
        style={glowStyle}
      />

      {/* Floating Particles */}
      {[...Array(15)].map((_, i) => (
        <motion.span
          key={i}
          style={{
            ...particle,
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`
          }}
          animate={{ y: [-15, 15, -15] }}
          transition={{ duration: 4 + i, repeat: Infinity }}
        />
      ))}

      {/* Card */}
      <motion.div
        ref={cardRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={resetTilt}
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        style={cardStyle}
      >
        <h2 style={{ color: theme.colors.primary }}>
          Create Account
        </h2>

        {success ? (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
            style={successStyle}
          >
            ✓ Account Created Successfully
          </motion.div>
        ) : (
          <>
            <form onSubmit={handleSubmit} style={formStyle}>

              {/* Email */}
              <div style={inputWrapper}>
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  onFocus={() => setFocused("email")}
                  onBlur={() => setFocused(null)}
                  style={inputStyle}
                />
                <label
                  style={{
                    ...labelStyle,
                    top:
                      focused === "email" || form.email
                        ? "-8px"
                        : "12px",
                    fontSize:
                      focused === "email" || form.email
                        ? "12px"
                        : "14px",
                    color:
                      focused === "email"
                        ? theme.colors.primary
                        : "#777"
                  }}
                >
                  Email
                </label>
              </div>

              {/* Password */}
              <div style={inputWrapper}>
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  onFocus={() => setFocused("password")}
                  onBlur={() => setFocused(null)}
                  style={{ ...inputStyle, paddingRight: "40px" }}
                />
                <label
                  style={{
                    ...labelStyle,
                    top:
                      focused === "password" || form.password
                        ? "-8px"
                        : "12px",
                    fontSize:
                      focused === "password" || form.password
                        ? "12px"
                        : "14px",
                    color:
                      focused === "password"
                        ? theme.colors.primary
                        : "#777"
                  }}
                >
                  Password
                </label>

                <span
                  onClick={() => setShowPassword(!showPassword)}
                  style={eyeStyle}
                >
                  {showPassword ? <FiEyeOff /> : <FiEye />}
                </span>
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ color: theme.colors.danger }}
                >
                  {error}
                </motion.p>
              )}

              <motion.button
                whileTap={{ scale: 0.95 }}
                whileHover={{ scale: 1.05 }}
                disabled={loading}
                type="submit"
                style={buttonStyle}
              >
                {loading ? "Creating..." : "Signup"}
              </motion.button>
            </form>

            {/* Redirect Link */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              style={{
                fontSize: "14px",
                textAlign: "center",
                marginTop: "10px"
              }}
            >
              Already have an account?{" "}
              <motion.span
                onClick={() => navigate("/login")}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={{
                  color: theme.colors.primary,
                  cursor: "pointer",
                  fontWeight: "600",
                  borderBottom: `1px solid ${theme.colors.primary}`
                }}
              >
                Login
              </motion.span>
            </motion.p>
          </>
        )}
      </motion.div>
    </div>
  );
}

/* ---------------- STYLES ---------------- */

const containerStyle = {
  height: "100vh",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  background: theme.colors.background,
  position: "relative",
  overflow: "hidden"
};

const glowStyle = {
  position: "absolute",
  width: "500px",
  height: "500px",
  borderRadius: "50%",
  background: theme.colors.primary,
  opacity: 0.1,
  filter: "blur(120px)"
};

const particle = {
  position: "absolute",
  width: "6px",
  height: "6px",
  borderRadius: "50%",
  background: theme.colors.primary,
  opacity: 0.2
};

const cardStyle = {
  width: "400px",
  padding: "40px",
  borderRadius: theme.radius.lg,
  background: "rgba(255,255,255,0.6)",
  backdropFilter: "blur(20px)",
  boxShadow: theme.shadow.soft,
  display: "flex",
  flexDirection: "column",
  gap: "20px",
  zIndex: 2,
  transition: "0.2s ease"
};

const formStyle = {
  display: "flex",
  flexDirection: "column",
  gap: "25px"
};

const inputWrapper = {
  position: "relative"
};

const inputStyle = {
  width: "100%",
  padding: "12px",
  borderRadius: "10px",
  border: "1px solid #ddd",
  outline: "none"
};

const labelStyle = {
  position: "absolute",
  left: "12px",
  background: "rgba(255,255,255,0.9)",
  padding: "0 4px",
  transition: "0.2s ease"
};

const eyeStyle = {
  position: "absolute",
  right: "12px",
  top: "12px",
  cursor: "pointer",
  color: "#777"
};

const buttonStyle = {
  padding: "12px",
  borderRadius: "12px",
  border: "none",
  background: theme.colors.primary,
  color: "#fff",
  fontWeight: "600",
  cursor: "pointer"
};

const successStyle = {
  textAlign: "center",
  padding: "20px",
  background: theme.colors.primary,
  color: "#fff",
  borderRadius: "12px"
};