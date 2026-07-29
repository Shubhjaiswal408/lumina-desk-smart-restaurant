import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Copy, RefreshCw, Webhook, QrCode } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { getPay, getPayments, getToken, useKitchen, type PayInfo, type Payment } from "@/lib/api"

const when = (ts: number | null) =>
  ts ? new Date(ts * 1000).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"

const copy = (t: string) => { navigator.clipboard?.writeText(t); toast.success("Copied") }

export default function Payments() {
  const { orders } = useKitchen()
  const [table, setTable] = useState("07")
  const [amount, setAmount] = useState("")
  const [pay, setPay] = useState<PayInfo | null>(null)
  const [rows, setRows] = useState<Payment[]>([])

  const loadRows = () => getPayments().then(setRows)
  useEffect(() => { loadRows(); const t = setInterval(loadRows, 4000); return () => clearInterval(t) }, [])

  // Prefill the amount from that table's live bill
  useEffect(() => {
    const o = orders.find((x) => x.table === table)
    if (o && !amount) setAmount(String(Math.round(o.total)))
  }, [orders, table, amount])

  const generate = async () => {
    const info = await getPay(table, amount ? Number(amount) : undefined)
    setPay(info); loadRows()
  }

  const origin = location.origin
  const webhookUrl = `${origin}/api/pay/webhook`

  return (
    <div className="p-6">
      <header className="mb-5">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Payments</h1>
        <p className="text-sm text-muted-foreground">
          Dynamic UPI QR — only the <code className="text-primary">am</code> (amount) changes per bill
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-3 mb-6">
        {/* Generator */}
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="flex items-center gap-2"><QrCode className="size-4" /> Generate QR</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-end gap-3 mb-4">
              <div className="w-24">
                <label className="text-xs text-muted-foreground">Table</label>
                <Input value={table} onChange={(e) => setTable(e.target.value)} />
              </div>
              <div className="w-36">
                <label className="text-xs text-muted-foreground">Amount ₹</label>
                <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="auto from bill" />
              </div>
              <Button onClick={generate} className="gap-1.5"><RefreshCw className="size-4" /> Generate</Button>
              {orders.length > 0 && (
                <div className="text-xs text-muted-foreground ml-auto">
                  Live tables: {orders.map((o) => `T${o.table} ₹${Math.round(o.total)}`).join(" · ")}
                </div>
              )}
            </div>

            {pay ? (
              <div className="flex flex-wrap gap-6 items-start">
                {/* <img> can't send the auth header, so the token rides along in
                    the query string (the guard accepts either). */}
                <img src={`${pay.qr}&token=${encodeURIComponent(getToken())}`}
                  alt="UPI QR" className="size-52 rounded-lg bg-white p-2" />
                <div className="flex-1 min-w-64 space-y-3 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Amount encoded</div>
                    <div className="font-display text-3xl font-semibold text-primary tabular-nums">
                      ₹{pay.amount.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Payee (VPA)</div>
                    <div className="font-mono">{pay.vpa} · {pay.payee}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Txn reference (matched by webhook)</div>
                    <div className="font-mono">{pay.ref}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">UPI deep link</div>
                    <div className="flex gap-2">
                      <code className="flex-1 break-all rounded bg-muted px-2 py-1.5 text-[11px]">{pay.upi_url}</code>
                      <Button size="icon" variant="secondary" onClick={() => copy(pay.upi_url)}><Copy className="size-4" /></Button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-8 text-center">
                Pick a table and press Generate to create a dynamic QR.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Webhook details */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Webhook className="size-4" /> Webhook</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Give this URL to your PSP</div>
              <div className="flex gap-2">
                <code className="flex-1 break-all rounded bg-muted px-2 py-1.5 text-[11px]">{webhookUrl}</code>
                <Button size="icon" variant="secondary" onClick={() => copy(webhookUrl)}><Copy className="size-4" /></Button>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground mb-1">Expected POST body</div>
              <pre className="rounded bg-muted p-2 text-[11px] overflow-x-auto">{`{
  "ref": "LUM07…",
  "status": "success",
  "amount": 1250.00
}`}</pre>
            </div>
            <p className="text-[11px] text-muted-foreground">
              This is a LAN address. A real gateway needs a public URL — expose it
              via a tunnel (cloudflared / ngrok) or a static IP + port-forward.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden py-0">
        <div className="px-4 py-3 border-b bg-card/60 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Payment log
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Reference</TableHead>
              <TableHead className="w-20">Table</TableHead>
              <TableHead className="w-28 text-right">Amount</TableHead>
              <TableHead className="w-28">Status</TableHead>
              <TableHead className="w-44 text-right">Settled</TableHead>
              <TableHead className="w-28" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                No payments yet.
              </TableCell></TableRow>
            )}
            {rows.map((p) => (
              <TableRow key={p.ref}>
                <TableCell className="font-mono text-xs">{p.ref}</TableCell>
                <TableCell><Badge variant="outline">T{p.tbl}</Badge></TableCell>
                <TableCell className="text-right font-semibold">₹{Math.round(p.amount)}</TableCell>
                <TableCell>
                  <Badge className={
                    p.status === "paid" ? "bg-emerald-500/15 text-emerald-500 border-0"
                    : p.status === "failed" ? "bg-red-500/15 text-red-500 border-0"
                    : "bg-amber-500/15 text-amber-500 border-0"}>
                    {p.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right text-muted-foreground text-sm">{when(p.settled_at)}</TableCell>
                <TableCell className="text-right">
                  {p.status === "pending" && (
                    <Button size="sm" variant="secondary" onClick={async () => {
                      await fetch(`/api/payments/${p.ref}/mark`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ paid: true }),
                      })
                      toast.success("Marked paid"); loadRows()
                    }}>Mark paid</Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
