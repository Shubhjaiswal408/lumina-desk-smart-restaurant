import { useEffect, useState } from "react"
import { HashRouter, Routes, Route, NavLink, Navigate } from "react-router-dom"
import { ChefHat, BarChart3, UtensilsCrossed, History, QrCode, TerminalSquare, Settings as SettingsIcon, Lock as LockIcon } from "lucide-react"
import { Toaster } from "@/components/ui/sonner"
import Kitchen from "./pages/Kitchen"
import Analytics from "./pages/Analytics"
import Menu from "./pages/Menu"
import Orders from "./pages/Orders"
import Payments from "./pages/Payments"
import Logs from "./pages/Logs"
import Lock from "./pages/Lock"
import SettingsPage from "./pages/Settings"
import { getToken, clearToken } from "@/lib/api"

const NAV = [
  { to: "/kitchen", label: "Kitchen", icon: ChefHat },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/menu", label: "Menu", icon: UtensilsCrossed },
  { to: "/payments", label: "Payments", icon: QrCode },
  { to: "/orders", label: "Orders", icon: History },
  { to: "/terminal", label: "Terminal", icon: TerminalSquare },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
]

function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r bg-card/40 flex flex-col">
      <div className="flex items-center gap-3 px-5 h-16 border-b">
        <div className="size-3.5 rotate-45 rounded-[3px] bg-primary" />
        <div className="leading-none">
          <div className="font-display text-xl font-semibold tracking-[0.12em]">LUMINA</div>
          <div className="text-[9px] font-semibold tracking-[0.38em] text-muted-foreground mt-1.5">
            CONSOLE
          </div>
        </div>
      </div>
      <nav className="p-3 flex flex-col gap-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto p-3">
        <button onClick={() => { clearToken(); location.reload() }}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium
                     text-muted-foreground hover:bg-accent hover:text-foreground">
          <LockIcon className="size-4" /> Lock console
        </button>
        <div className="px-3 pt-3 text-[11px] text-muted-foreground">
          Lumina Desk · Kitchen &amp; Backend
        </div>
      </div>
    </aside>
  )
}

export default function App() {
  const [open, setOpen] = useState(!!getToken())
  useEffect(() => { document.documentElement.classList.add("dark") }, [])
  if (!open) return <Lock onOpen={() => setOpen(true)} />
  return (
    <HashRouter>
      <div className="flex h-screen bg-background text-foreground">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/kitchen" replace />} />
            <Route path="/kitchen" element={<Kitchen />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/menu" element={<Menu />} />
            <Route path="/payments" element={<Payments />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/terminal" element={<Logs />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
      <Toaster position="top-right" richColors />
    </HashRouter>
  )
}
