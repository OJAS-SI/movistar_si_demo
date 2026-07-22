# Movistar Service Intelligence Twin — customer demo script

**Presenter:** Future Space SA · **Audience:** Telefónica / Movistar
**Target length:** 5:00 · **Narration budget:** ~750 words at 150 wpm

Every figure below is taken from the actual warm `full` run in the app
(seed 20260629 · 2 401 homes · 41 access nodes · 6 regions · 576 intervals at 5-minute
cadence = **48 hours of network time**). If the seed changes, re-run the facts block at
the end of this file and update the three deep-dive numbers.

---

## Timing map

| # | Section | In | Out | Words |
|---|---------|----|-----|-------|
| 1 | Future Space | 0:00 | 0:25 | 62 |
| 2 | The console — what you are looking at | 0:25 | 1:05 | 100 |
| 3 | Telemetry, interval by interval | 1:05 | 1:30 | 62 |
| 4 | Movistar's problem — the three use cases | 1:30 | 2:20 | 125 |
| 5 | Run the simulation | 2:20 | 2:45 | 62 |
| 6 | Three faults, in depth | 2:45 | 4:15 | 225 |
| 7 | Four fields, no prior learning | 4:15 | 4:40 | 62 |
| 8 | Ready to deploy | 4:40 | 5:00 | 52 |
| | | | **5:00** | **750** |

---

## 1 · Future Space — 0:00–0:25

> **ON SCREEN** Future Space logo (white mark, `image3.svg`) on the console's dark
> background. Brand blue `#1265FF`. Strapline: *Donde el futuro se hace presente*.

**NARRATION**

> Future Space builds Structural Intelligence — an AI that reasons on physical rules and
> network topology rather than on large labelled histories.
>
> It reads a fault as a *shape* on the service graph. That is why it learns from very
> little data, and why it suits critical infrastructure, where data is scarce, sensitive,
> or simply not labelled.
>
> What follows is Movistar Service Intelligence: our engagement with Telefónica, running
> live.

---

## 2 · The console — 0:25–1:05

> **ON SCREEN** Analyst tab, `tiny` scale, run complete. Cursor moves panel to panel as
> each is named.

**NARRATION**

> This is the operator console. On the left, the alert rail — every fault the engine has
> named, newest at the top.
>
> Pinned beneath it, the honest instruments: what the engine *refused* to say. Decoys
> that fired, the false-positive rate, quiet intervals watched.
>
> Centre: the shape on the graph, and the four-beat narrative — stream, form, predict,
> prescribe.
>
> Right: the call, and the certified-decision receipt — the claim, the evidence, an
> independent cross-check, and where every number came from.
>
> Along the bottom, the run on a timeline.

---

## 3 · Telemetry, interval by interval — 1:05–1:30

> **ON SCREEN** Hover the three ribbon legend keys — each tooltip explains its mark.
> Then hover the magnitude trace behind the marks.

**NARRATION**

> Every element on the network reports one number, every interval — set-top boxes, home
> gateways, access nodes, core routes, content sources.
>
> That is the blue trace on the ribbon: the only thing the engine is allowed to read. No
> error codes. No alarms. No labels.
>
> Red marks are where a fault truly began. Green is where the engine named the element
> responsible. The gap between them is the operator's warning.

---

## 4 · Movistar's problem — 1:30–2:20

> **ON SCREEN** Three cards or lower-thirds, one per use case. Keep the console visible
> behind them.

**NARRATION**

> Three problems, from the Telefónica engagement.
>
> **One — network nodes.** A fault at an access node surfaces as scattered, unexplained
> complaints across nearby homes. By the time they correlate, many homes are already
> degraded and technicians are being sent to the wrong place.
>
> **Two — individual customers.** A household is only visible once it calls. The
> experience has usually been deteriorating for days.
>
> **Three — invisible faults.** Some problems carry no label at all, so current tooling
> sees nothing. The customer is told to restart, or the box is swapped — and the fault
> returns, because it was never in the box.
>
> One mechanism solves all three: the shape of who is affected, sharing what.

---

## 5 · Run the simulation — 2:20–2:45

> **ON SCREEN** Toggle `tiny → full` (instant). Press play. Ribbon runs 60 s at 1× —
> let it run under the next section. Optionally 2× to finish sooner.

**NARRATION**

> This is a synthetic model of a Telefónica-style Spanish network — no Movistar data.
> Two thousand four hundred homes, forty-one access nodes, six regions, forty-eight hours
> of network time.
>
> Twenty-four faults are injected, plus three decoys designed to tempt a false alarm.
>
> Because every fault is injected, every answer is scored against a known truth.

---

## 6 · Three faults, in depth — 2:45–4:15

> **ON SCREEN** Click each alert in turn; let the receipt and recommended action show.

### 6a · Use case 1 — the node (0:30)

> **Madrid metro · OLT-2800001-01 · interval 80 → named 87 · 06:40 → 07:15**

> Madrid metro. Twenty homes behind access node OLT-2800001-01 begin to drift at 06:40.
> By 07:15 the engine has named the node — a mean departure of seven and a half standard
> deviations above each home's own learned baseline, and all twenty sit behind that one
> node on the network map.
>
> A shared parent is the attribution: the fault is at the access node, not in any home.
> Recommended — inspect the access node and its aggregation, before complaints escalate.
> That is a hundred and ten minutes of warning.

### 6b · Use case 2 — the household (0:25)

> **Madrid metro · STB-2800002-02-010 · interval 207 → named 220 · 17:15 → 18:20**

> A single household, STB-2800002-02-010. One home elevated, sustained — and every peer
> on its access node at baseline.
>
> Isolation is the attribution: the cause is inside this home. Recommended — proactive
> contact and a gateway reconfiguration. No truck roll.
>
> Four hours before the customer would have noticed.

### 6c · Use case 3 — the invisible fault (0:35)

> **A Coruña · OLT-1500001-01 · interval 357 → named 365 · day 2, 05:45 → 06:25**

> A Coruña. Five homes, a recurring impairment, and no error code anywhere in the data —
> the case today's tooling cannot see.
>
> A set-top box swap is simulated mid-fault. The signature is unchanged across it. The box
> is exonerated.
>
> The engine places the fault in the access segment at ninety-two percent confidence.
> Box-swap discrimination: one hundred percent. Recommended — investigate the segment,
> and stop dispatching replacement boxes.

---

## 7 · Four fields, no prior learning — 4:15–4:40

> **ON SCREEN** Cut to the four field names, then back to the honest instruments panel.

**NARRATION**

> Everything you have just seen was derived from four fields per element, per interval.
>
> `entity_src` — where the reading came from. `entity_dst` — its parent in the service
> path. `timestamp` — which interval. `magnitude` — the impairment on that edge.
>
> Source and destination are an edge. Time slots it into an interval. Magnitude is the
> weight. That is a weighted graph over time — the same record NetFlow has used for
> twenty years.
>
> No training run. No labelled history. The engine learns each edge's normal from the
> stream itself — and it held fire on all three decoys, at zero false positives.

---

## 8 · Ready to deploy — 4:40–5:00

> **ON SCREEN** Management tab: 24/24 detected · 0.0% false positives · decoys held 3/3.

**NARRATION**

> Telemetry already converges inside Telefónica before it reaches us. We connect where it
> is already gathered — one integration point, two at most. Never element by element.
>
> We can start entirely offline, on roughly a month of already-stored, anonymised data —
> no integration into operational systems.
>
> **[TIMELINE — see decision note]** and you have a working prototype on Movistar's own
> data.

---

## Decisions needed before recording

1. **Timeline — 4–6 or 4–8 weeks?** You said *4 to 6 weeks*. The customer deck says
   **4–8 weeks from data receipt** (`Movistar_Use_Cases_EN_FINAL.pptx`, slides 18 and 20).
   Contradicting your own deck on camera is worse than the extra fortnight. Recommend
   saying **"four to eight weeks from data receipt"**, or amend the deck first.

2. **"Real time" — say it carefully.** The deck positions Option 1 as *offline, on ~1
   month of historical data*, and Option 2 as *(near) real-time*. The engine runs on
   intervals, and slide N3a says a small lag is irrelevant. The script therefore says
   *"interval by interval"* and *"as the network reports"* rather than "real time". If you
   want the phrase, use **"near real time"** — it is defensible; unqualified "real time"
   is not, for Option 1.

3. **Confidence is not a probability.** If asked: it is a weighted score over three
   measured ratios — concentration, departure strength, and topological fit. Do not
   present 92% as "92% likely".

4. **Say "synthetic" out loud once** (it is in §5). The console carries a *Synthetic
   demo* badge; the narration must match it, or the room may believe this ran on their
   network.

5. **Order.** You asked for panels before the problem statement, and the script follows
   that. If the room is commercial rather than technical, moving §4 ahead of §2 lands
   better — the *why* before the *what*. Trivial to swap; the timings are unchanged.

---

## Facts block — regenerate if the seed changes

```
run: full · seed 20260629 · 2401 homes · 41 access nodes · 6 regions
     576 intervals @ 300 s = 48 h of network time
totals: 24 faults · 24/24 detected · false positives 0.0% (0 of 89 quiet intervals)
        decoys fired 0/3 · self-test PASS · mean lead time 44.4 min

UC1  OLT-2800001-01   Madrid metro   access/cluster  20 homes
     onset 80 (06:40) → named 87 (07:15)   lead 110 min   conf 77%   7.5σ
UC2  STB-2800002-02-010  Madrid metro  home/single   1 home
     onset 207 (17:15) → named 220 (18:20)  lead 255 min  conf 73%   6.9σ
UC3  OLT-1500001-01   A Coruña       access/cluster  5 homes
     onset 357 (05:45+1d) → named 365 (06:25+1d)  lead 75 min  conf 92%  8.8σ
     box-swap discrimination 100%
```

Regenerate with the app running on :8001 —
`curl -s "http://127.0.0.1:8001/api/runs/<full run_id>/console?lang=en"`.

---

## Branding assets extracted from the template

`Documents/brand-extract/` — pulled from `[Plantilla_PPT] FutureSpace_LIGERA_2026`.

| asset | use |
|---|---|
| `image3.svg` | logo mark, **white** — for the console's dark header |
| `image1.svg` | logo mark, brand blue `#1265FF` |
| `image4.svg` | wordmark, 750×150 |

**Palette (theme):** `#1265FF` primary · `#0A2E73` deep navy · `#3C8DFF` / `#66B3FF`
light accents · `#0A275C` · `#E8F2FF` · `#2A2E35` ink · **Arial**.

Note the console's existing cyan `#19B3F0` is *not* the brand blue. The rebrand is a
separate task — this script does not depend on it.
