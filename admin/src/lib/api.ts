import { useEffect, useRef, useState } from "react"

export type Item = {
  name: string; qty: number; size?: string; status: string; is_new: boolean
  allergens: string[]; veg: boolean; category: string; prep: number
}
export type Order = {
  table: string; items: Item[]; subtotal: number; tax: number; total: number
  eta: number; status: string; staff_called: boolean; pay_requested: boolean
  created: number; updated: number
}
export type MenuItem = {
  name: string; category: string; veg: boolean; vegan: boolean
  allergens: string[]; prep: number; price: number; available: boolean; custom?: boolean
}
export type Analytics = {
  revenue_today: number; orders_today: number; avg_ticket: number
  avg_turnaround_min: number; total_served: number
  popular: { name: string; qty: number }[]
  revenue_by_hour: { hour: string; revenue: number }[]
  busiest_tables: { table: string; orders: number; revenue: number }[]
  peak_hour: string; peak_hour_orders: number
}
export type HistoryOrder = {
  id: number; table: string; items: { name: string; qty: number; size?: string }[]
  total: number; created: number; served_at: number
}

export type PayInfo = {
  table: string; amount: number; upi_url: string; ref: string; qr: string
  vpa: string; payee: string
}
export type Payment = {
  ref: string; tbl: string; amount: number; status: string
  created: number; settled_at: number | null
}

// Mirrors menu.label_for on the Pi: a real size leads ("Large Margherita"),
// anything else trails ("Classic Aloo Tikki Burger (Amul Cheese Slice)").
const TRUE_SIZES = new Set(["regular", "medium", "large", "small"])
export const dishLabel = (name: string, size?: string) =>
  !size ? name : TRUE_SIZES.has(size.toLowerCase()) ? `${size} ${name}` : `${name} (${size})`

// --- auth (staff PIN) ---
export const getToken = () => localStorage.getItem("lumina_token") || ""
export const setToken = (t: string) => localStorage.setItem("lumina_token", t)
export const clearToken = () => localStorage.removeItem("lumina_token")

export async function login(pin: string): Promise<boolean> {
  const r = await fetch("/api/auth", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin }),
  })
  if (!r.ok) return false
  const d = await r.json()
  if (d.token) { setToken(d.token); return true }
  return false
}

/** fetch with the staff token; bounces to the PIN screen on 401. */
async function authFetch(p: string, init?: RequestInit) {
  const r = await fetch(p, {
    ...init,
    headers: { ...(init?.headers || {}), "x-lumina-token": getToken() },
  })
  if (r.status === 401) { clearToken(); location.reload() }
  return r
}

const j = (p: string) => authFetch(p).then((r) => r.json())
export type Settings = {
  mode: string; assistant_state: string
  groq_api_key_masked?: string; has_key?: boolean; ollama_up?: boolean
  restaurant_name: string; table_id: string
  tax_mode: string; tax_rate: number; upi_vpa: string; upi_payee: string
  feedback_url: string; wake_threshold: number; vad_silence_sec: number
  reply_language: string
}
export const getSettings = () => j("/api/settings") as Promise<Settings>
export const saveSettings = (patch: Record<string, unknown>) => post("/api/settings", patch)
export const testSettings = (groq_api_key?: string) =>
  post("/api/settings/test", { groq_api_key }) as Promise<
    { cloud_ok: boolean; ollama_up: boolean; detail: string }>

export const getPay = (table: string, amount?: number) =>
  j(`/api/pay/${table}${amount != null ? `?amount=${amount}` : ""}`) as Promise<PayInfo>
export const getPayments = () => j("/api/payments") as Promise<Payment[]>
export const getLogs = (service: string, lines = 150) =>
  j(`/api/logs?service=${service}&lines=${lines}`) as Promise<{ service: string; lines: string[] }>
export const getMenu = () => j("/api/menu") as Promise<MenuItem[]>
export const getAnalytics = () => j("/api/analytics") as Promise<Analytics>
export const getHistory = () => j("/api/orders/history") as Promise<HistoryOrder[]>
export const post = (p: string, body?: unknown) =>
  authFetch(p, { method: "POST", headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined }).then((r) => r.json())

/** Live kitchen state over WebSocket (auto-reconnect). */
export type ServiceReq = { item: string; qty: number; at: number }
export type TableInfo = { table: string; state: string; service: ServiceReq[] }

export function useKitchen() {
  const [orders, setOrders] = useState<Order[]>([])
  const [tables, setTables] = useState<TableInfo[]>([])
  const [now, setNow] = useState(Date.now() / 1000)
  const [connected, setConnected] = useState(false)
  const seen = useRef<Set<string>>(new Set())
  const onNew = useRef<() => void>(() => {})

  useEffect(() => {
    let ws: WebSocket
    let stop = false

    // Paint from a plain fetch first: the socket can take a moment (or be
    // blocked entirely, e.g. a headless browser), and staff shouldn't stare at
    // an empty board while it negotiates.
    j("/api/state").then((m) => {
      if (!stop && m?.orders) { setOrders(m.orders); setNow(m.now); setTables(m.tables || []) }
    }).catch(() => {})

    const connect = () => {
      ws = new WebSocket(`ws://${location.host}/ws?token=${encodeURIComponent(getToken())}`)
      ws.onopen = () => setConnected(true)
      ws.onclose = () => { setConnected(false); if (!stop) setTimeout(connect, 1500) }
      ws.onmessage = (e) => {
        const m = JSON.parse(e.data)
        if (m.type === "state") {
          const fresh = m.orders.some(
            (o: Order) => !seen.current.has(o.table) || o.items.some((i) => i.is_new))
          const tables = new Set<string>(m.orders.map((o: Order) => o.table))
          m.orders.forEach((o: Order) => seen.current.add(o.table))
          seen.current.forEach((t) => { if (!tables.has(t)) seen.current.delete(t) })
          setOrders(m.orders); setNow(m.now); setTables(m.tables || [])
          if (fresh) onNew.current()
        }
      }
    }
    connect()
    const tick = setInterval(() => setNow((n) => n + 1), 1000)
    return () => { stop = true; ws?.close(); clearInterval(tick) }
  }, [])

  return { orders, tables, now, connected, onNew }
}
