import { useState } from "react"
import { Lock as LockIcon, Delete } from "lucide-react"
import { Button } from "@/components/ui/button"
import { login } from "@/lib/api"

export default function Lock({ onOpen }: { onOpen: () => void }) {
  const [pin, setPin] = useState("")
  const [err, setErr] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = async (value: string) => {
    setBusy(true)
    const ok = await login(value)
    setBusy(false)
    if (ok) onOpen()
    else { setErr(true); setPin(""); setTimeout(() => setErr(false), 1200) }
  }

  const press = (d: string) => {
    const next = (pin + d).slice(0, 6)
    setPin(next)
    if (next.length === 4) submit(next)     // 4-digit PIN auto-submits
  }

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-background text-foreground">
      <div className="flex items-center gap-3 mb-2">
        <div className="size-3.5 rotate-45 rounded-[3px] bg-primary" />
        <div className="font-display text-2xl font-semibold tracking-[0.12em]">LUMINA</div>
      </div>
      <p className="text-xs tracking-[0.35em] text-muted-foreground mb-10">CONSOLE</p>

      <div className={`flex items-center gap-3 mb-8 ${err ? "animate-pulse" : ""}`}>
        <LockIcon className={`size-4 ${err ? "text-destructive" : "text-muted-foreground"}`} />
        <div className="flex gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className={`size-3.5 rounded-full border-2 transition-colors ${
              err ? "border-destructive"
              : i < pin.length ? "bg-primary border-primary" : "border-muted-foreground/40"}`} />
          ))}
        </div>
      </div>
      <p className={`h-5 text-sm mb-4 ${err ? "text-destructive" : "text-muted-foreground"}`}>
        {err ? "Wrong PIN" : busy ? "Checking…" : "Enter staff PIN"}
      </p>

      <div className="grid grid-cols-3 gap-3">
        {["1","2","3","4","5","6","7","8","9"].map((d) => (
          <Button key={d} variant="secondary" className="size-20 text-2xl font-semibold"
            onClick={() => press(d)}>{d}</Button>
        ))}
        <div />
        <Button variant="secondary" className="size-20 text-2xl font-semibold"
          onClick={() => press("0")}>0</Button>
        <Button variant="ghost" className="size-20" onClick={() => setPin(pin.slice(0, -1))}>
          <Delete className="size-5" />
        </Button>
      </div>
    </div>
  )
}
