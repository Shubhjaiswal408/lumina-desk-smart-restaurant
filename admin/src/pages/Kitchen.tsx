import { useEffect, useRef } from "react"
import { Bell, CreditCard, Wifi, WifiOff, Utensils, TriangleAlert, RotateCcw,
  BrushCleaning, CalendarCheck, X, HandPlatter } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useKitchen, post, dishLabel, type Order, type Item, type TableInfo } from "@/lib/api"

function chime() {
  try {
    const a = new AudioContext()
    ;[880, 1320].forEach((f, i) => {
      const o = a.createOscillator(), g = a.createGain()
      o.frequency.value = f; o.connect(g); g.connect(a.destination)
      const t = a.currentTime + i * 0.16
      g.gain.setValueAtTime(0.0001, t)
      g.gain.exponentialRampToValueAtTime(0.25, t + 0.02)
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.3)
      o.start(t); o.stop(t + 0.32)
    })
  } catch { /* ignore */ }
}

const mins = (s: number) => (s < 60 ? "<1m" : `${Math.floor(s / 60)}m`)

const statusColor: Record<string, string> = {
  new: "bg-muted text-muted-foreground",
  preparing: "bg-amber-500/15 text-amber-500",
  ready: "bg-emerald-500/15 text-emerald-500",
  served: "bg-muted text-muted-foreground",
}

function ItemRow({ o, i }: { o: Order; i: Item }) {
  return (
    <button
      onClick={() => post(`/api/table/${o.table}/item/${encodeURIComponent(i.name)}/advance`)}
      className="w-full flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-accent/60 text-left"
    >
      <span className={`size-3 rounded-sm border-2 ${i.veg ? "border-emerald-500" : "border-red-500"} relative`}>
        <span className={`absolute inset-[3px] rounded-full ${i.veg ? "bg-emerald-500" : "bg-red-500"}`} />
      </span>
      <span className="font-bold text-red-500 w-7">{i.qty}×</span>
      <span className="font-medium flex-1">{dishLabel(i.name, i.size)}</span>
      {i.allergens.length > 0 && (
        <span className="flex items-center gap-1 text-[11px] text-red-500">
          <TriangleAlert className="size-3" />{i.allergens.join(", ")}
        </span>
      )}
      <Badge className={`${statusColor[i.status]} border-0 uppercase text-[10px]`}>{i.status}</Badge>
    </button>
  )
}

const STATE_STYLE: Record<string, string> = {
  occupied: "bg-primary/15 text-primary border-primary/40",
  reserved: "bg-sky-500/15 text-sky-400 border-sky-500/40",
  cleaning: "bg-amber-500/15 text-amber-500 border-amber-500/40",
  available: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
}

function TableBoard({ tables }: { tables: TableInfo[] }) {
  if (!tables.length) return null
  return (
    <div className="flex flex-wrap items-center gap-2 mb-5">
      <span className="text-xs uppercase tracking-wider text-muted-foreground mr-1">Tables</span>
      {tables.map((t) => (
        <div key={t.table}
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm ${STATE_STYLE[t.state]}`}>
          <b>T{t.table}</b>
          <span className="text-xs capitalize">{t.state}</span>
          {t.state === "cleaning" && (
            <button title="Mark clean" className="hover:opacity-70"
              onClick={() => post(`/api/table/${t.table}/state/available`)}>
              <BrushCleaning className="size-3.5" />
            </button>
          )}
          {t.state === "available" && (
            <button title="Reserve" className="hover:opacity-70"
              onClick={() => post(`/api/table/${t.table}/state/reserved`)}>
              <CalendarCheck className="size-3.5" />
            </button>
          )}
          {t.state === "reserved" && (
            <button title="Free the table" className="hover:opacity-70"
              onClick={() => post(`/api/table/${t.table}/state/available`)}>
              <X className="size-3.5" />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

export default function Kitchen() {
  const { orders, tables, now, connected, onNew } = useKitchen()
  const first = useRef(true)
  useEffect(() => { onNew.current = () => { if (!first.current) chime(); first.current = false } }, [onNew])

  const sorted = [...orders].sort((a, b) => a.created - b.created)
  const items = sorted.reduce((n, o) => n + o.items.reduce((k, i) => k + i.qty, 0), 0)

  return (
    <div className="p-6">
      <header className="flex items-center gap-4 mb-5">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Kitchen Display</h1>
          <p className="text-sm text-muted-foreground">Live tickets from every table</p>
        </div>
        <div className="ml-auto flex items-center gap-6 text-sm">
          <div className="text-center"><div className="text-2xl font-bold">{sorted.length}</div>
            <div className="text-[10px] uppercase text-muted-foreground tracking-wider">Orders</div></div>
          <div className="text-center"><div className="text-2xl font-bold">{items}</div>
            <div className="text-[10px] uppercase text-muted-foreground tracking-wider">Items</div></div>
          <Badge variant="outline" className="gap-1.5">
            {connected ? <Wifi className="size-3.5 text-emerald-500" /> : <WifiOff className="size-3.5 text-red-500" />}
            {connected ? "Live" : "Offline"}
          </Badge>
        </div>
      </header>

      <TableBoard tables={tables} />

      <div className="space-y-2 mb-5">
        {/* Guest asked for water / napkin / cutlery — staff must deliver it */}
        {tables.filter((t) => t.service.length > 0).map((t) => (
          <div key={"sv" + t.table}
            className="flex items-center gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-emerald-300 font-medium">
            <HandPlatter className="size-5" />
            Table {t.table} needs: {t.service.map((s) => `${s.qty}× ${s.item}`).join(", ")}
            <Button size="sm" variant="secondary" className="ml-auto"
              onClick={() => post(`/api/table/${t.table}/service/clear`)}>Delivered</Button>
          </div>
        ))}
        {sorted.filter((o) => o.staff_called).map((o) => (
          <div key={"s" + o.table} className="flex items-center gap-3 rounded-xl border border-blue-500/40 bg-blue-500/10 px-4 py-3 text-blue-300 font-medium animate-pulse">
            <Bell className="size-5" /> Staff needed at Table {o.table}
            <Button size="sm" variant="secondary" className="ml-auto"
              onClick={() => post(`/api/table/${o.table}/ack_alert/staff`)}>Got it</Button>
          </div>
        ))}
        {sorted.filter((o) => o.pay_requested).map((o) => (
          <div key={"p" + o.table} className="flex items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-amber-300 font-medium animate-pulse">
            <CreditCard className="size-5" /> Payment requested — Table {o.table} · ₹{Math.round(o.total)}
            <Button size="sm" variant="secondary" className="ml-auto"
              onClick={() => post(`/api/table/${o.table}/ack_alert/pay`)}>Got it</Button>
          </div>
        ))}
      </div>

      {sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-muted-foreground h-[55vh]">
          <Utensils className="size-14 mb-4 opacity-40" />
          <p className="text-lg">All caught up</p>
          <p className="text-sm">No active orders</p>
        </div>
      ) : (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
          {sorted.map((o) => {
            const wait = now - o.created
            const tone = wait > 600 ? "text-red-500" : wait > 300 ? "text-amber-500" : "text-emerald-500"
            const fresh = o.items.some((i) => i.is_new)
            return (
              <Card key={o.table} className={`overflow-hidden ${fresh ? "ring-2 ring-red-500/60" : ""}`}>
                <div className="flex items-center gap-2 px-4 pb-3 border-b">
                  <div className="text-xl font-extrabold">Table {o.table}</div>
                  <div className={`ml-auto font-bold tabular-nums ${tone}`}>{mins(wait)}</div>
                </div>
                <div className="p-2">
                  {o.items.map((i) => <ItemRow key={i.name} o={o} i={i} />)}
                </div>
                <div className="flex gap-2 p-3 border-t">
                  <Button size="sm" className="flex-1 bg-amber-500 hover:bg-amber-500/90 text-black"
                    onClick={() => post(`/api/table/${o.table}/all/preparing`)}>Start</Button>
                  <Button size="sm" className="flex-1 bg-emerald-500 hover:bg-emerald-500/90 text-black"
                    onClick={() => post(`/api/table/${o.table}/all/ready`)}>Ready</Button>
                  <Button size="sm" variant="secondary"
                    onClick={() => post(`/api/table/${o.table}/bump`)}>Served</Button>
                  <Button size="sm" variant="ghost" title="Clear ticket & reset the guest's voice session"
                    onClick={() => post(`/api/table/${o.table}/reset`)}>
                    <RotateCcw className="size-4" />
                  </Button>
                  <span className="ml-auto self-center font-bold">₹{Math.round(o.total)}</span>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
