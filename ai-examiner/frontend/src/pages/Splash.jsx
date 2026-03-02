import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { theme } from "../theme/theme";
import { useState } from "react";

export default function Splash() {
  const navigate = useNavigate();
  const [isNavigating, setIsNavigating] = useState(false);

  const handleNavigate = (path) => {
    setIsNavigating(true);
    setTimeout(() => navigate(path), 500);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.5 }}
      style={{
        height: "100vh",
        width: "100%",
        position: "relative",
        overflow: "hidden",
        background: theme.colors.background
      }}
    >
      {/* 🔳 Animated Moving Grid */}
      <motion.div
        animate={{ backgroundPosition: ["0px 0px", "0px 40px"] }}
        transition={{ repeat: Infinity, duration: 6, ease: "linear" }}
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(to right, rgba(92,64,51,0.07) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(92,64,51,0.07) 1px, transparent 1px)
          `,
          backgroundSize: "40px 40px",
          zIndex: 0
        }}
      />

      {/* 🌫 Soft Glow Background */}
      <motion.div
        animate={{ scale: [1, 1.1, 1] }}
        transition={{ repeat: Infinity, duration: 8 }}
        style={{
          position: "absolute",
          width: "600px",
          height: "600px",
          borderRadius: "50%",
          background: theme.colors.primary,
          opacity: 0.05,
          filter: "blur(150px)",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 0
        }}
      />

      {/* 🧊 Main Glass Card */}
      <motion.div
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -40, opacity: 0 }}
        transition={{ duration: 0.6 }}
        style={{
          height: "100%",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          position: "relative",
          zIndex: 2
        }}
      >
        <motion.div
          whileHover={{ scale: 1.02 }}
          transition={{ type: "spring", stiffness: 200 }}
          style={{
            backdropFilter: "blur(20px)",
            background: "rgba(255,255,255,0.4)",
            borderRadius: theme.radius.lg,
            padding: "60px 80px",
            boxShadow: theme.shadow.soft,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "25px",
            border: "1px solid rgba(255,255,255,0.3)"
          }}
        >
          {/* 🔥 Title + Animated Underline with Sweep */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center"
            }}
          >
            <motion.h1
              initial={{ letterSpacing: "20px", opacity: 0 }}
              animate={{ letterSpacing: "2px", opacity: 1 }}
              transition={{ duration: 1 }}
              style={{
                fontSize: "42px",
                color: theme.colors.primary,
                fontWeight: "700"
              }}
            >
              AI Examiner
            </motion.h1>

            {/* Animated Underline Container */}
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: "180px", opacity: 1 }}
              transition={{ delay: 0.8, duration: 0.8 }}
              style={{
                height: "4px",
                marginTop: "14px",
                borderRadius: "20px",
                position: "relative",
                overflow: "hidden",
                background: `rgba(92,64,51,0.2)`
              }}
            >
              {/* Moving Light Sweep */}
              <motion.div
                animate={{ x: ["-100%", "100%"] }}
                transition={{
                  repeat: Infinity,
                  duration: 2.5,
                  ease: "linear"
                }}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "50%",
                  height: "100%",
                  background: `linear-gradient(
                    90deg,
                    transparent,
                    ${theme.colors.primary},
                    transparent
                  )`,
                  opacity: 0.8
                }}
              />
            </motion.div>
          </div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.7 }}
            transition={{ delay: 1 }}
            style={{
              color: theme.colors.textSecondary,
              fontSize: "15px"
            }}
          >
            Intelligent Examination Management System
          </motion.p>

          {/* 🔘 Buttons */}
          <div style={{ display: "flex", gap: "20px", marginTop: "20px" }}>
            <motion.button
              whileHover={{
                scale: 1.05,
                boxShadow: theme.shadow.hover
              }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleNavigate("/login")}
              style={{
                padding: "14px 40px",
                borderRadius: theme.radius.lg,
                border: "none",
                background: theme.colors.primary,
                color: "white",
                fontSize: "16px",
                cursor: "pointer"
              }}
            >
              Login
            </motion.button>

            <motion.button
              whileHover={{
                scale: 1.05,
                boxShadow: theme.shadow.hover
              }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleNavigate("/signup")}
              style={{
                padding: "14px 40px",
                borderRadius: theme.radius.lg,
                border: `1px solid ${theme.colors.primary}`,
                background: "transparent",
                color: theme.colors.primary,
                fontSize: "16px",
                cursor: "pointer"
              }}
            >
              Signup
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}