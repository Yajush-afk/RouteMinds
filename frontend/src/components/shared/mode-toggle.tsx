import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";

export function ModeToggle() {
  const { theme, setTheme } = useTheme();

  // Toggle function
  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={toggleTheme}
    >
      {/* Sun icon (visible in light mode) */}
      <Sun className="h-[1.2rem] w-[1.2rem] transition-all dark:hidden" />

      {/* Moon icon (visible in dark mode) */}
      <Moon className="h-[1.2rem] w-[1.2rem] hidden dark:block" />

      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
