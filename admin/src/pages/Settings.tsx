import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Cloud, CloudOff, Zap, CheckCircle2, XCircle, Save, Mic, MicOff, PowerOff } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { getSettings, saveSettings, testSettings, type Settings as S } from "@/lib/api"

const ASSISTANT_STATES = [
  { id: "active", icon: Mic, label: "Active",
    desc: "Listening and speaking normally." },
  { id: "muted", icon: MicOff, label: "Muted",
    desc: "Microphone closed — nothing is heard or said. The screen and the table's buttons still work, and the right-hand button turns it back on." },
  { id: "off", icon: PowerOff, label: "Off",
    desc: "Microphone closed and the table's mute button is disabled. Only staff can switch it back on, from here." },
]

const MODES = [
  { id: "auto", icon: Zap, label: "Auto (recommended)",
    desc: "Cloud when the internet is up, local brain automatically if it drops. Best of both." },
  { id: "online", icon: Cloud, label: "Online",
    desc: "Always cloud — Groq Whisper + Llama 70B. Fastest and most accurate. Needs internet + API key." },
  { id: "offline", icon: CloudOff, label: "Offline",
    desc: "Everything on the Pi — Vosk + LFM2. No internet at all. Slower and less accurate, but always works." },
]

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-3 py-2.5 border-b last:border-0">
      <div className="min-w-52">
        <div className="text-sm font-medium">{label}</div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </div>
      <div className="flex-1 min-w-48">{children}</div>
    </div>
  )
}

export default function SettingsPage() {
  const [s, setS] = useState<S | null>(null)
  const [key, setKey] = useState("")
  const [pin, setPin] = useState("")
  const [busy, setBusy] = useState(false)
  const [health, setHealth] = useState<{ cloud_ok: boolean; ollama_up: boolean; detail: string } | null>(null)

  const load = () => getSettings().then(setS)
  useEffect(() => { load() }, [])
  if (!s) return <div className="p-6 text-muted-foreground">Loading…</div>

  const save = async (patch: Partial<S> & { groq_api_key?: string; admin_pin?: string }) => {
    setBusy(true)
    await saveSettings(patch)
    setBusy(false)
    toast.success("Saved — applies within a second, no restart")
    setKey("")
    load()
  }

  const test = async () => {
    setBusy(true)
    setHealth(await testSettings(key || undefined))
    setBusy(false)
  }

  return (
    <div className="p-6 max-w-4xl">
      <header className="mb-5">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Changes apply live — no restart needed</p>
      </header>

      {/* Assistant on/off/mute */}
      <Card className="mb-4">
        <CardHeader><CardTitle>Assistant</CardTitle></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          {ASSISTANT_STATES.map((a) => {
            const active = s.assistant_state === a.id
            return (
              <button key={a.id} onClick={() => save({ assistant_state: a.id })}
                className={`text-left rounded-xl border p-4 transition-colors ${
                  active ? "border-primary bg-primary/10" : "hover:bg-accent/50"}`}>
                <a.icon className={`size-5 mb-2 ${active ? "text-primary" : "text-muted-foreground"}`} />
                <div className="font-semibold text-sm">{a.label}</div>
                <div className="text-xs text-muted-foreground mt-1">{a.desc}</div>
              </button>
            )
          })}
        </CardContent>
      </Card>

      {/* Mode */}
      <Card className="mb-4">
        <CardHeader><CardTitle>Brain mode</CardTitle></CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-3">
          {MODES.map((m) => {
            const active = s.mode === m.id
            return (
              <button key={m.id} onClick={() => save({ mode: m.id })}
                className={`text-left rounded-xl border p-4 transition-colors ${
                  active ? "border-primary bg-primary/10" : "hover:bg-accent/50"}`}>
                <m.icon className={`size-5 mb-2 ${active ? "text-primary" : "text-muted-foreground"}`} />
                <div className="font-semibold text-sm">{m.label}</div>
                <div className="text-xs text-muted-foreground mt-1">{m.desc}</div>
              </button>
            )
          })}
        </CardContent>
      </Card>

      {/* Cloud key */}
      <Card className="mb-4">
        <CardHeader><CardTitle>Cloud (Groq) API key</CardTitle></CardHeader>
        <CardContent>
          <Row label="API key" hint={s.groq_api_key_masked ? `Currently: ${s.groq_api_key_masked}` : "Not set"}>
            <div className="flex gap-2">
              <Input type="password" placeholder="gsk_…" value={key}
                onChange={(e) => setKey(e.target.value)} />
              <Button disabled={!key || busy} onClick={() => save({ groq_api_key: key })}>Save</Button>
            </div>
          </Row>
          <Row label="Health check" hint="Verify the key and the local brain">
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="secondary" onClick={test} disabled={busy}>Test now</Button>
              {health && (
                <>
                  <Badge variant="outline" className={health.cloud_ok ? "text-emerald-500" : "text-red-500"}>
                    {health.cloud_ok ? <CheckCircle2 className="size-3 mr-1" /> : <XCircle className="size-3 mr-1" />}
                    Cloud
                  </Badge>
                  <Badge variant="outline" className={health.ollama_up ? "text-emerald-500" : "text-red-500"}>
                    {health.ollama_up ? <CheckCircle2 className="size-3 mr-1" /> : <XCircle className="size-3 mr-1" />}
                    Local (offline brain)
                  </Badge>
                  <span className="text-xs text-muted-foreground">{health.detail}</span>
                </>
              )}
            </div>
          </Row>
        </CardContent>
      </Card>

      {/* Billing */}
      <Card className="mb-4">
        <CardHeader><CardTitle>Billing &amp; payments</CardTitle></CardHeader>
        <CardContent>
          <Row label="Tax mode" hint="How GST appears on the bill">
            <select value={s.tax_mode} onChange={(e) => save({ tax_mode: e.target.value })}
              className="h-9 rounded-md border bg-transparent px-2 text-sm">
              <option value="inclusive">Included in menu prices</option>
              <option value="exclusive">Added on top</option>
              <option value="none">No tax</option>
            </select>
          </Row>
          <Row label="Tax rate %" >
            <Input type="number" defaultValue={s.tax_rate} className="w-28"
              onBlur={(e) => { const v = Number(e.target.value); if (v !== s.tax_rate) save({ tax_rate: v }) }} />
          </Row>
          <Row label="UPI ID (VPA)" hint="Where the money lands">
            <Input defaultValue={s.upi_vpa}
              onBlur={(e) => e.target.value !== s.upi_vpa && save({ upi_vpa: e.target.value })} />
          </Row>
          <Row label="Payee name" hint="Shown in the guest's UPI app">
            <Input defaultValue={s.upi_payee}
              onBlur={(e) => e.target.value !== s.upi_payee && save({ upi_payee: e.target.value })} />
          </Row>
          <Row label="Feedback form URL"
            hint={'QR on the thank-you screen. Must be reachable from a phone on mobile data, ' +
                  'so use a public form. Tip: in Google Forms use ⋮ → "Get pre-filled link", ' +
                  'type TABLE as the answer to your table question, and paste that link here — ' +
                  'every response will say which table it came from.'}>
            <Input placeholder="https://docs.google.com/forms/…?entry.123456=TABLE"
              defaultValue={s.feedback_url}
              onBlur={(e) => e.target.value !== s.feedback_url && save({ feedback_url: e.target.value })} />
          </Row>
        </CardContent>
      </Card>

      {/* Access */}
      <Card className="mb-4">
        <CardHeader><CardTitle>Console access</CardTitle></CardHeader>
        <CardContent>
          <Row label="Staff PIN" hint="4 digits. Everyone stays logged in until they lock or the server restarts.">
            <div className="flex gap-2">
              <Input type="password" inputMode="numeric" maxLength={6} placeholder="new PIN"
                value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} />
              <Button disabled={pin.length < 4 || busy}
                onClick={async () => { await save({ admin_pin: pin }); setPin("")
                  toast.success("PIN changed — it applies to the next login") }}>
                Change PIN
              </Button>
            </div>
          </Row>
        </CardContent>
      </Card>

      {/* Voice */}
      <Card>
        <CardHeader><CardTitle>Voice tuning</CardTitle></CardHeader>
        <CardContent>
          <Row label="Restaurant name">
            <Input defaultValue={s.restaurant_name}
              onBlur={(e) => e.target.value !== s.restaurant_name && save({ restaurant_name: e.target.value })} />
          </Row>
          <Row label="Wake sensitivity" hint="Lower = triggers more easily (0.3–0.7)">
            <Input type="number" step="0.05" defaultValue={s.wake_threshold} className="w-28"
              onBlur={(e) => { const v = Number(e.target.value); if (v !== s.wake_threshold) save({ wake_threshold: v }) }} />
          </Row>
          <Row label="End-of-speech pause (s)" hint="How long a silence ends the guest's sentence">
            <Input type="number" step="0.1" defaultValue={s.vad_silence_sec} className="w-28"
              onBlur={(e) => { const v = Number(e.target.value); if (v !== s.vad_silence_sec) save({ vad_silence_sec: v }) }} />
          </Row>
          <p className="text-xs text-muted-foreground pt-3">
            <Save className="size-3 inline mr-1" />
            Wake sensitivity applies when the voice service next restarts.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
