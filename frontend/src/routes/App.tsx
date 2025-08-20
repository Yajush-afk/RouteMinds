import { ThemeProvider } from "@/components/theme-provider";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import { Route, Routes } from "react-router-dom";
import NotFoundPage from "@/pages/NotFoundPage";
function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="theme">
      <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
