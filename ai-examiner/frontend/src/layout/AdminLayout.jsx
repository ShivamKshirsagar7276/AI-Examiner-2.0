import { motion } from "framer-motion";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { theme } from "../theme/theme";

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  const menuItems = [
    { name: "Dashboard", path: "/dashboard" },
    { name: "Exams", path: "/exams" },
    { name: "Results", path: "/results" }
  ];

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      
      {/* 🟤 Sidebar */}
      <div
        style={{
          width: "240px",
          background: `linear-gradient(180deg, ${theme.colors.primary}, ${theme.colors.primaryDark})`,
          color: "white",
          padding: "30px 20px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between"
        }}
      >
        {/* Logo */}
        <div>
          <h2 style={{ marginBottom: "40px" }}>AI Examiner</h2>

          {menuItems.map((item) => (
            <motion.div
              key={item.path}
              whileHover={{ scale: 1.05 }}
              onClick={() => navigate(item.path)}
              style={{
                padding: "12px 15px",
                borderRadius: "10px",
                marginBottom: "10px",
                cursor: "pointer",
                background:
                  location.pathname === item.path
                    ? "rgba(255,255,255,0.2)"
                    : "transparent"
              }}
            >
              {item.name}
            </motion.div>
          ))}
        </div>

        {/* Logout */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          onClick={handleLogout}
          style={{
            padding: "10px",
            borderRadius: "10px",
            border: "none",
            background: theme.colors.danger,
            color: "white",
            cursor: "pointer"
          }}
        >
          Logout
        </motion.button>
      </div>

      {/* 📄 Main Content */}
      <div
        style={{
          flex: 1,
          background: theme.colors.background,
          padding: "30px",
          overflowY: "auto"
        }}
      >
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Outlet />
        </motion.div>
      </div>
    </div>
  );
}