import { useEffect, useState } from "react"
import { Card } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { getHistory, dishLabel, type HistoryOrder } from "@/lib/api"

const when = (ts: number) =>
  new Date(ts * 1000).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })

export default function Orders() {
  const [rows, setRows] = useState<HistoryOrder[]>([])
  useEffect(() => {
    const load = () => getHistory().then(setRows)
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="p-6">
      <header className="mb-5">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Orders</h1>
        <p className="text-sm text-muted-foreground">Served order history · {rows.length} shown</p>
      </header>

      <Card className="overflow-hidden py-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">#</TableHead>
              <TableHead className="w-20">Table</TableHead>
              <TableHead>Items</TableHead>
              <TableHead className="w-28 text-right">Total</TableHead>
              <TableHead className="w-40 text-right">Served</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-16">
                No completed orders yet.
              </TableCell></TableRow>
            )}
            {rows.map((o) => (
              <TableRow key={o.id}>
                <TableCell className="text-muted-foreground">{o.id}</TableCell>
                <TableCell><Badge variant="outline">T{o.table}</Badge></TableCell>
                <TableCell className="text-sm">
                  {o.items.map((i) => `${i.qty}× ${dishLabel(i.name, i.size)}`).join(", ")}
                </TableCell>
                <TableCell className="text-right font-semibold">₹{Math.round(o.total)}</TableCell>
                <TableCell className="text-right text-muted-foreground text-sm">{when(o.served_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
