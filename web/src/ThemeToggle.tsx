import { useState } from "react"
import { Moon, Sun } from "lucide-react"

// index.html sets data-theme before the first paint, from the saved choice or the system's.
export function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === "dark")
  function flip() {
    const theme = dark ? "light" : "dark"
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem("theme", theme)
    } catch {
      // Private windows can refuse storage; the choice then lasts for this visit.
    }
    setDark(!dark)
  }
  return (
    <button type="button" className="ghost icon-btn" onClick={flip} aria-label={dark ? "Switch to light mode" : "Switch to dark mode"} title={dark ? "Light mode" : "Dark mode"}>
      {dark ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}
    </button>
  )
}
