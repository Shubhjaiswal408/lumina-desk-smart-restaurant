# Lumina Desk — demo script

**[Download as PDF](Lumina-Desk-demo-script.pdf)** — same thing, printable.

Two halves. First what a customer sees at the table, then what the restaurant
sees behind it. Shoot them in that order — the second only makes sense once the
first has landed.

> **Before you roll.** Run `./venv/bin/python tools_doctor.py` — everything should
> say ok. Open `http://techiesms.local:8000` and log in now, so no PIN screen
> appears on camera. Leave 20–30 seconds between takes; the free API tier slows
> down under rapid retries.

---

## Part 1 · The customer

### Sitting down

*Shot: over your shoulder — table, panel, nothing else.*

The screen is already showing the restaurant name and three things you could say.
No app, no QR code, no menu card.

### Ordering

> **You:** *Hey Lumina, one large Margherita and two cold coffees.*

It answers out loud, and the panel redraws with both items, the prices, what they
contain, and the running total.

> **The screen takes about 20 seconds to redraw.** That's ePaper, not a bug. Say
> the number out loud once and the audience accepts it for the rest of the video.
> Then cut away or speed it up in the edit — never film the wait.

### Asking about the food

> **You:** *What's in the cheese stuffed garlic bread?*

It reads the ingredients. Worth saying on camera: this comes out of the menu
database, not the model's memory. It isn't allowed to make it up.

> **You:** *Add two of those.*

"Those" works — it knows what you were just talking about.

### Changing your mind

> **You:** *Actually, remove one.*
>
> **You:** *What's my bill?*

The total is computed in Python from the menu. The model never touches a number —
that's the line worth repeating.

### Paying

> **You:** *I want to pay.*

*Shot: the panel with the UPI QR, then your own phone scanning it.*

The amount is already filled in. One UPI ID, a different amount every bill, no
payment gateway. Pay it for real if you can — a live payment landing is worth
more than any explanation.

Then the thank-you screen, with a feedback QR that already knows which table you
were sitting at.

### One more thing worth showing

*Action: pull the internet out, on camera.*

> **You:** *Hey Lumina, one Margherita.*

It still works. Wake word, speech recognition, understanding, the voice and the
screen all run on the Pi. Be straight that offline recognition is less accurate —
admitting it costs nothing and makes the rest believable.

---

## Part 2 · The kitchen and the back office

Screen recording from here, not a camera pointed at a monitor. Everything lives
at one address on the restaurant's WiFi.

### The kitchen board

Tickets appear as they're spoken. Wait timers turn amber then red. Allergens are
flagged in red on every line. One tap moves a dish New → Preparing → Ready →
Served, and the table's own screen updates with it.

*Shot: order something at the table, then cut to the ticket appearing.*

Guest requests get their own banner — "Table 07 needs 2× water" — and stay up
until someone marks them delivered.

### Changing the menu, live

The best single demo in the whole back office. Do it in one shot, no cut:

1. Change a dish's price on the Menu page
2. Immediately ask Lumina what that dish costs
3. The new price comes back

Same for marking something sold out — it stops being orderable straight away. No
restart, no redeploy.

### Analytics

Revenue today, average ticket, how long an order takes from spoken to served,
peak hour, busiest tables, and what people actually order.

### Payments

Every bill and how it settled. Payments confirm themselves by reading the
merchant's payment emails; there's a webhook for a real gateway and a **Mark
paid** button for when neither applies.

### Terminal

Live logs from every service, in the browser. Show yourself debugging a table
from a phone while standing in the shop — that's the point of it.

### Settings

Assistant on, muted or off. Cloud or fully offline. Tax, UPI ID, the voice and
how fast it speaks, wake-word sensitivity, staff PIN. Everything applies within a
second.

Worth demonstrating **Muted** specifically: the microphone is genuinely released —
the mic ring goes dark — and the table's screen says so instead of inviting
someone to talk to something that isn't listening.

---

## What to say, and what not to

| Say | Why it lands |
|---|---|
| The model never decides a price. | It's the whole design in six words. |
| Pull the internet out and it keeps taking orders. | Nobody expects this. |
| The screen uses no power to hold that bill. | The moment people rewind. |
| It's running at a real pizza place, with their real menu. | Turns a demo into a product. |

**Don't say it's perfect.** It mishears a dish name sometimes, like every voice
system. If that happens mid-take, correct it out loud and keep rolling — that
take is better than a clean one, because every voice demo online is suspiciously
flawless and everyone knows it.

---

## Rough edges to plan around

| Thing | What to do |
|---|---|
| ePaper takes ~20 s to redraw | Cut away or speed-ramp. Mention the number once. |
| The very first word of a reply can clip | Don't subtitle a greeting or make it a hero moment. Every line is written so losing the first word doesn't lose the meaning. |
| Free API tier rate-limits | 20–30 s between takes. |
| Panel is on USB | The WiFi firmware works, but this router has client isolation on. Don't claim battery on camera unless you've shot it. |
| Offline is slower | Say so. That it works at all is the feature. |

---

## If you want one clip for social

Sit down. Say the order. Cut to the panel showing the bill. No narration,
vertical, fifteen seconds. The idea reads without a word of explanation, which is
the only thing that travels.
