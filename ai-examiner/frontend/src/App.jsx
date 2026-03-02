import AppRouter from "./app/router";
import { theme } from "./theme/theme";

function App() {
  return (
    <div
      style={{
        backgroundColor: theme.colors.background,
        minHeight: "100vh",
        fontFamily: "Inter, sans-serif"
      }}
    >
      <AppRouter />
    </div>
  );
}

export default App;