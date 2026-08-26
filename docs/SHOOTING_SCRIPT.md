# Lumina Desk — shooting script

A shot list, not an essay. Written around what this build actually does well and
what it doesn't, so nothing surprises you on the day.

---

## Before you roll — 10 minutes

```bash
cd ~/lumina-desk
./venv/bin/python tools_doctor.py        # every backend, one screen
```

Everything should say `ok`. If the chat model line is red, Groq has retired
another one — fix that before shooting, not during.

Then:

| Check | Why it matters on camera |
|---|---|
| Panel USB cable in, `ls /dev/ttyUSB*` | The panel runs over USB. WiFi needs client isolation turned off on the router. |
| `http://techiesms.local:8000` opens | You'll cut to this. Log in once now so no PIN screen on camera. |
| Room reasonably quiet | The wake word is fine in a normal room, but an AC directly overhead will cost you takes. |
| Groq free tier | It rate-limits under rapid retries. Space out your takes or you'll get slow replies that aren't representative. |

**Reset to a clean table before each ordering take:**
```bash
TOK=$(curl -s -X POST localhost:8000/api/auth -H 'Content-Type: application/json' \
  -d "{\"pin\":\"$(./venv/bin/python -c 'import settings;print(settings.get("admin_pin"))')\"}" \
  | ./venv/bin/python -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -X POST localhost:8000/api/table/07/reset -H "x-lumina-token: $TOK"
```

---

## The one thing to plan around

**A colour ePaper refresh takes about 26 seconds.** Never film a screen update in
real time — it's dead air and it will read as "broken" to a viewer.

Three ways to handle it, use all of them:

1. Cut away to your face or the kitchen dashboard while it draws.
2. Speed-ramp the refresh 8–10× in the edit. It looks like magic; real time looks
   like a hang.
3. Shoot the panel *after* it has settled, as a clean insert.

Say the number out loud once — "this takes about twenty seconds, that's ePaper" —
and the audience forgives it for the rest of the video. Hiding it is what makes
people suspicious.

---

## Shot list

### 1 · Cold open (0:00–0:15)

No talking. Sit down at the table like a customer.

- **Shot:** over-the-shoulder, table + panel in frame
- **Action:** *"Hey Lumina, one large Margherita and two cold coffees."*
- **Cut to:** the panel, already showing the order and the bill
- **Cut to:** the kitchen dashboard, ticket appearing

Then the title.

The whole pitch is in those fifteen seconds: no app, no menu, no waiter. Don't
explain yet.

### 2 · The problem (0:15–0:45)

Face to camera. Keep it short.

> You sit down. You wait for a menu. You wait for someone to come. You wait
> again for the bill. I put a microphone and a paper screen on a table so you
> don't have to wait for any of it.

Mention it's running at a real outlet — Auntyno-Z Pizza in Ghodasar, all 189
dishes from their actual menu. That's the line that makes it a product rather
than a demo.

### 3 · The hardware (0:45–2:00)

B-roll, name each part as you show it.

| Part | Line worth saying |
|---|---|
| Raspberry Pi 5 | Everything runs here. No server. |
| reSpeaker XVF3800 | Four mics with beamforming. This is why it hears you across a table. |
| reTerminal E1002 | 7.5" colour ePaper. Draws nothing when idle — that's why it can run on battery. |

Hold up the panel with a bill on it and say it's using **zero power** to show it.
That's the moment people rewind.

### 4 · A full order, uncut (2:00–3:30)

The heart of the video. One take, no cuts inside it, so nobody thinks it's edited
together. Say these, in this order:

```
"Hey Lumina, what pizzas do you have?"
"One large Margherita."
"What's in the cheese stuffed garlic bread?"
"Add two of those."
"Actually, remove one."
"What's my bill?"
```

Why these six: they show the section summary, an order with a size, an allergen
answer from the database, a pronoun ("those") resolving, a correction, and the
maths — without you narrating any of it.

**If it mishears a dish, keep rolling and correct it out loud.** That take is
better than a clean one. Every voice demo on YouTube is suspiciously perfect and
everybody knows it.

### 5 · The part that earns trust (3:30–4:30)

This is what separates it from an LLM demo. Face to camera, with the code up.

> The model never decides a price. It works out what you meant — then the
> prices, the totals and the allergens all come out of a Python file. It cannot
> bill you for a dish that doesn't exist, because the name is checked against
> the menu first.

Show `menu.py` briefly, and then the guard in `llm.py`.

Then the honest bit, which is the most quotable thing in the video:

> Ask it what's in a dish and it isn't allowed to answer from memory. It has to
> read the database. That's the difference between a demo and something you'd
> put in a restaurant.

### 6 · Unplug the internet (4:30–5:15)

Do it on camera. Physically.

- **Action:** pull the WiFi / turn off the hotspot
- **Action:** *"Hey Lumina, one Margherita."*
- It still works.

> Wake word, speech recognition, understanding, the voice, the screen — all of
> it on the Pi. A restaurant doesn't get to stop taking orders because the
> internet went down.

Be straight that offline speech recognition is less accurate than the cloud. The
admission costs you nothing and buys the whole video's credibility.

### 7 · Paying (5:15–6:00)

```
"Hey Lumina, I want to pay."
```

- **Cut to:** the panel with the UPI QR
- **Action:** scan it with your own phone, on camera, and show the amount is
  already filled in
- Say: one UPI ID, a different amount per bill, no payment gateway

Then the thank-you screen. If you have a feedback form set up, mention that the
QR on it already knows which table you were sitting at.

### 8 · The staff side (6:00–7:00)

Screen recording, not a camera pointed at a monitor.

Walk through: **Kitchen** (live tickets, allergens in red, wait timers) →
**Analytics** (revenue, peak hour, popular dishes) → **Menu** (change a price and
say it's live for the voice immediately) → **Terminal** (logs in a browser, no
SSH).

The Menu page is the one to linger on. Edit a price, then immediately ask Lumina
for that dish and let the new price come back. One shot, no cut.

### 9 · Close (7:00–7:30)

- Repo is public, link below
- One Pi per table is the real cost — be upfront
- What you'd build next

---

## Lines that will land, and one to avoid

**Say:**
- "The model never decides a price."
- "Pull the internet out and it keeps taking orders."
- "The screen uses no power to hold that bill."
- "It's running at a real pizza place, with their real menu."

**Don't say** "it's perfect" or "it never gets anything wrong." It mishears
dish names sometimes, like every voice system. Show a correction instead — it
makes the rest believable.

---

## Known rough edges — plan around them, don't hide them

| Thing | What to do |
|---|---|
| ePaper takes ~26s to redraw | Cut away or speed-ramp. Mention the number once. |
| The very first word of a reply can clip | Don't subtitle the greeting or make it a hero moment. Every line is written so the first word can be lost without losing the meaning — but don't draw attention to it. |
| Groq free tier rate-limits | Leave 20–30 s between takes. Back-to-back retries produce slow replies that aren't how it normally behaves. |
| Panel is on USB | If someone asks about battery, say the WiFi firmware is written and works — this router has client isolation on. Don't claim battery on camera unless you've shot it. |
| Offline is slower | Say so. It's a feature that it works at all. |

---

## If you want one clip for social

Seconds 0:00–0:15 above, vertical, no narration, hard cut to the panel showing
the bill. The whole idea reads without a word of explanation, which is the only
thing that travels.
