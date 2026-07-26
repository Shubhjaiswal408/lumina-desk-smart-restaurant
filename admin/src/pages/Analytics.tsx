import { useEffect, useState, type ElementType } from "react"
import { IndianRupee, Receipt, Timer, TrendingUp } from "lucide-react"
import { BarChart, Bar, XAxis, ResponsiveContainer, Cell } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getAnalytics, type Analytics as A } from "@/lib/api"

function Stat({ icon: Icon, label, value, sub, accent }: {
  icon: ElementType; label: string; value: string; sub?: string; accent?: boolean
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{label}</span>
          <Icon className={`size-4 ${accent ? "text-primary" : "text-muted-foreground"}`} />
        </div>
        <div className={`font-display text-4xl font-semibold mt-2 tabular-nums ${accent ? "text-primary" : ""}`}>
          {value}
        </div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  )
}

export default function Analytics() {
  const [a, setA] = useState<A | null>(null)
  useEffect(() => {
    const load = () => getAnalytics().then(setA)
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  if (!a) return <div className="p-6 text-muted-foreground">Loading…</div>
  const maxHour = Math.max(...a.revenue_by_hour.map((h) => h.revenue), 1)
  const maxPop = Math.max(...a.popular.map((p) => p.qty), 1)

  return (
    <div className="p-6">
      <header className="mb-5">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">Today's performance · {a.total_served} orders served all-time</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        <Stat icon={IndianRupee} label="Revenue today" value={`₹${a.revenue_today.toLocaleString()}`} sub={`${a.orders_today} orders`} accent />
        <Stat icon={Receipt} label="Avg ticket" value={`₹${a.avg_ticket}`} />
        <Stat icon={Timer} label="Avg turnaround" value={`${a.avg_turnaround_min}m`} sub="order → served" />
        <Stat icon={TrendingUp} label="Peak hour" value={a.peak_hour || "—"}
          sub={a.peak_hour_orders ? `${a.peak_hour_orders} orders` : undefined} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Revenue by hour</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={a.revenue_by_hour}>
                <XAxis dataKey="hour" tickLine={false} axisLine={false}
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} interval={2} />
                <Bar dataKey="revenue" radius={[4, 4, 0, 0]}>
                  {a.revenue_by_hour.map((h, i) => (
                    <Cell key={i} fill={h.revenue >= maxHour * 0.66 ? "#ef4444" : "var(--primary)"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Busiest tables</CardTitle></CardHeader>
          <CardContent>
            {a.busiest_tables?.length ? (
              <div className="flex flex-wrap gap-3">
                {a.busiest_tables.map((t) => (
                  <div key={t.table} className="rounded-lg border px-4 py-3 min-w-28">
                    <div className="font-display text-2xl font-semibold">T{t.table}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {t.orders} orders · ₹{t.revenue.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted-foreground">No data yet.</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Popular dishes</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {a.popular.length === 0 && <p className="text-sm text-muted-foreground">No data yet.</p>}
            {a.popular.map((p) => (
              <div key={p.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{p.name}</span>
                  <span className="text-muted-foreground">{p.qty}</span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div className="h-full bg-red-500 rounded-full" style={{ width: `${(p.qty / maxPop) * 100}%` }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
