import { useEffect, useRef, useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { getLogs } from "@/lib/api"

const SERVICES = [
  { id: "lumina-voice", label: "Voice (Hey Lumina)" },
  { id: "lumina-display", label: "ePaper display" },
  { id: "lumina-kds", label: "Web server" },
  { id: "mosquitto", label: "MQTT broker" },
]

// Colourise the parts a human scans for.
function line(l: string, i: number) {
  const low = l.toLowerCase()
  const tone =
    low.includes("error") || low.includes("traceback") || low.includes("failed") ? "text-red-400"
    : low.includes("wake") ? "text-primary"
    : low.includes("guest said") ? "text-emerald-400"
    : low.includes("lumina/") || low.includes("[lumina") ? "text-sky-300"
    : "text-muted-foreground"
  return <div key={i} className={`whitespace-pre-wrap break-all ${tone}`}>{l}</div>
}

export default function Logs() {
  const [service, setService] = useState(SERVICES[0].id)
  const [lines, setLines] = useState<string[]>([])
  const [follow, setFollow] = useState(true)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let stop = false
    const load = () => getLogs(service).then((r) => { if (!stop) setLines(r.lines || []) })
    load()
    const t = setInterval(() => { if (follow) load() }, 3000)
    return () => { stop = true; clearInterval(t) }
  }, [service, follow])

  useEffect(() => { if (follow && box.current) box.current.scrollTop = box.current.scrollHeight }, [lines, follow])

  return (
    <div className="p-6">
      <header className="flex items-center gap-4 mb-5">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Terminal</h1>
          <p className="text-sm text-muted-foreground">Live service logs — see exactly what the table is doing</p>
        </div>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <Switch checked={follow} onCheckedChange={setFollow} />
          <span className="text-muted-foreground">{follow ? "Following" : "Paused"}</span>
        </div>
      </header>

      <div className="flex flex-wrap gap-2 mb-4">
        {SERVICES.map((s) => (
          <Button key={s.id} size="sm" variant={service === s.id ? "default" : "secondary"}
            onClick={() => setService(s.id)}>
            {s.label}
          </Button>
        ))}
      </div>

      <Card className="p-0 overflow-hidden">
        <div ref={box} className="h-[65vh] overflow-y-auto bg-black/40 p-4 font-mono text-[12px] leading-relaxed">
          {lines.length === 0
            ? <div className="text-muted-foreground">No output.</div>
            : lines.map(line)}
        </div>
      </Card>
    </div>
  )
}
