import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Plus, Trash2 } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { getMenu, post, type MenuItem } from "@/lib/api"

const CATEGORIES = ["Starter", "Main", "Bread", "Rice", "Dessert", "Beverage"]
const blank = { name: "", category: "Main", price: "", veg: true, allergens: "", prep: "15", ingredients: "" }

export default function Menu() {
  const [items, setItems] = useState<MenuItem[]>([])
  const [filter, setFilter] = useState("")
  const [nd, setNd] = useState({ ...blank })
  const [adding, setAdding] = useState(false)

  const load = () => getMenu().then(setItems)
  useEffect(() => { load() }, [])

  const savePrice = (m: MenuItem, price: number) => {
    setItems((xs) => xs.map((x) => (x.name === m.name ? { ...x, price } : x)))
    post(`/api/menu/${encodeURIComponent(m.name)}`, { price }).then(() => toast.success(`${m.name} → ₹${price}`))
  }
  const toggle = (m: MenuItem, available: boolean) => {
    setItems((xs) => xs.map((x) => (x.name === m.name ? { ...x, available } : x)))
    post(`/api/menu/${encodeURIComponent(m.name)}`, { available })
      .then(() => toast[available ? "success" : "warning"](`${m.name} ${available ? "available" : "86'd (out)"}`))
  }
  const addDish = async () => {
    if (!nd.name.trim() || !nd.price) { toast.error("Name and price required"); return }
    setAdding(true)
    await post("/api/menu/add", {
      name: nd.name.trim(), category: nd.category, price: Number(nd.price), veg: nd.veg,
      prep: Number(nd.prep) || 15,
      allergens: nd.allergens.split(",").map((s) => s.trim()).filter(Boolean),
      ingredients: nd.ingredients.split(",").map((s) => s.trim()).filter(Boolean),
    })
    toast.success(`Added ${nd.name.trim()}`)
    setNd({ ...blank }); setAdding(false); load()
  }
  const del = (m: MenuItem) => {
    post(`/api/menu/${encodeURIComponent(m.name)}/delete`).then(() => { toast.success(`Removed ${m.name}`); load() })
  }

  const cats = [...new Set(items.map((i) => i.category))]
  const shown = items.filter((i) => i.name.toLowerCase().includes(filter.toLowerCase()))

  return (
    <div className="p-6">
      <header className="flex items-center gap-4 mb-5">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Menu</h1>
          <p className="text-sm text-muted-foreground">{items.length} dishes · add dishes, edit prices, mark sold out</p>
        </div>
        <Input placeholder="Search dishes…" value={filter} onChange={(e) => setFilter(e.target.value)}
          className="ml-auto max-w-xs" />
      </header>

      {/* Add a new dish — becomes orderable by voice immediately */}
      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-40">
            <label className="text-xs text-muted-foreground">Dish name</label>
            <Input value={nd.name} onChange={(e) => setNd({ ...nd, name: e.target.value })} placeholder="e.g. Tandoori Prawns" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Category</label>
            <select value={nd.category} onChange={(e) => setNd({ ...nd, category: e.target.value })}
              className="block h-9 rounded-md border bg-transparent px-2 text-sm">
              {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="w-24">
            <label className="text-xs text-muted-foreground">Price ₹</label>
            <Input type="number" value={nd.price} onChange={(e) => setNd({ ...nd, price: e.target.value })} />
          </div>
          <div className="w-20">
            <label className="text-xs text-muted-foreground">Prep min</label>
            <Input type="number" value={nd.prep} onChange={(e) => setNd({ ...nd, prep: e.target.value })} />
          </div>
          <div className="flex-1 min-w-40">
            <label className="text-xs text-muted-foreground">Allergens (comma)</label>
            <Input value={nd.allergens} onChange={(e) => setNd({ ...nd, allergens: e.target.value })} placeholder="dairy, nuts" />
          </div>
          <div className="flex-1 min-w-56">
            <label className="text-xs text-muted-foreground">Ingredients (comma) — Lumina answers from these</label>
            <Input value={nd.ingredients} onChange={(e) => setNd({ ...nd, ingredients: e.target.value })}
              placeholder="noodles, tomato, spices" />
          </div>
          <div className="flex items-center gap-2 pb-1.5">
            <Switch checked={nd.veg} onCheckedChange={(v) => setNd({ ...nd, veg: v })} />
            <span className="text-sm">{nd.veg ? "Veg" : "Non-veg"}</span>
          </div>
          <Button onClick={addDish} disabled={adding} className="gap-1.5">
            <Plus className="size-4" /> Add dish
          </Button>
        </div>
      </Card>

      {cats.map((cat) => {
        const rows = shown.filter((i) => i.category === cat)
        if (!rows.length) return null
        return (
          <Card key={cat} className="mb-4 overflow-hidden py-0">
            <div className="px-4 py-3 border-b bg-card/60 font-semibold text-sm uppercase tracking-wider text-muted-foreground">
              {cat}
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Dish</TableHead>
                  <TableHead>Diet</TableHead>
                  <TableHead>Allergens</TableHead>
                  <TableHead className="w-28">Price ₹</TableHead>
                  <TableHead className="w-24 text-right">Available</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((m) => (
                  <TableRow key={m.name} className={m.available ? "" : "opacity-50"}>
                    <TableCell className="font-medium">
                      {m.name}{m.custom && <Badge variant="outline" className="ml-2 text-primary text-[10px]">NEW</Badge>}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={m.veg ? "text-emerald-500" : "text-red-500"}>
                        {m.vegan ? "Vegan" : m.veg ? "Veg" : "Non-veg"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-red-500">
                      {m.allergens.length ? m.allergens.join(", ") : "—"}
                    </TableCell>
                    <TableCell>
                      <Input type="number" defaultValue={m.price} className="h-8 w-24"
                        onBlur={(e) => { const v = Number(e.target.value); if (v && v !== m.price) savePrice(m, v) }} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Switch checked={m.available} onCheckedChange={(v) => toggle(m, v)} />
                    </TableCell>
                    <TableCell>
                      {m.custom && (
                        <button onClick={() => del(m)} className="text-muted-foreground hover:text-red-500">
                          <Trash2 className="size-4" />
                        </button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )
      })}
    </div>
  )
}
