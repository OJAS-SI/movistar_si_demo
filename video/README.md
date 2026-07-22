# Demo video — automated pipeline

Produces `out/movistar-si-demo-es.mp4`: a ~5-minute Spanish customer demo of the Movistar
Service Intelligence Twin, narrated, with the area under discussion spotlit.

## Run it

```bash
# 1. the app must be up and the full run prewarmed (~85s after API start)
.venv/bin/uvicorn si_api.main:app --app-dir backend --host 127.0.0.1 --port 8001

# 2. narration  (key is never written to disk)
cd video
ELEVENLABS_API_KEY=sk_... node tts.mjs

# 3. screen recording - runs in real time, ~5.5 min
node record.mjs

# 4. composite
node build.mjs        # -> out/movistar-si-demo-es.mp4
```

`node record.mjs 06a-node` records a single segment, for checking pacing before
committing to a full pass.

## How it fits together

**`narration.json` is the single source of truth.** Each segment carries its Spanish
narration, the actions to perform (seek, click an alert by entity, switch tab), and the
beats — when to move the spotlight, and what to label it. Editing the script and editing
the choreography are the same edit, so they cannot drift apart.

**Audio drives timing, not the other way round.** `tts.mjs` renders one mp3 per segment;
`record.mjs` reads each file's real duration with ffprobe and holds the visuals for
exactly that long. Change a sentence and the visuals re-time themselves on the next run.
Until an mp3 exists, the planned `seconds` is used, so the recorder works before the
narration does.

**The recording is one continuous take.** Intro, console walkthrough and outro are all in
one Playwright video — nothing to stitch, no seam landing mid-sentence. The intro / use
cases / outro screens are `screens.html`, styled from the same brand tokens as the
console, so the cut between them and the live app is invisible. The logo is `fetch`ed
from `assets/fs-mark-white.svg`, the same file the console header uses.

**The spotlight is the real UI.** `spotlight(selector)` positions one overlay with a very
large `box-shadow`, dimming everything outside the element's rect and ringing it in brand
blue. Nothing is cloned, screenshotted or moved — what is highlighted is the live
component, so the video cannot show a stale rendering of a panel.

## Voice

Voice `dNjJKg63Fr5AXwIdkATa`, model `eleven_multilingual_v2`, stability 0.45 /
similarity 0.75 / style 0. Style stays at zero: this is narration, not performance.
Override with `ELEVENLABS_VOICE` / `ELEVENLABS_MODEL`.

## Content decisions baked in

- **Full scale only.** 2 401 homes, 41 access nodes, 6 regions, 576 intervals, 24 faults.
  The reduced scale is never shown - the richer run is the better demo.
- **"De cuatro a ocho semanas"** everywhere, matching
  `Documents/Movistar_Use_Cases_EN_FINAL.pptx` slides 18 and 20.
- **"Sintético" is said out loud** in section 5, matching the DEMO SINTÉTICA badge, so
  nobody can leave believing this ran on Telefónica's network.
- **"Intervalo a intervalo", never "tiempo real".** The deck positions the first option as
  offline over ~1 month of history; unqualified "real time" would overclaim it.
- Confidence is never described as a probability.

## Numbers quoted in the narration

Taken from the real seed-20260629 full run. If the seed changes, re-check them:

```
UC1  OLT-2800001-01     Madrid metro   20 hogares   1.8 h   77 %   7,5σ
UC2  STB-2800002-02-010 Madrid metro    1 hogar     4.3 h   73 %   6,9σ
UC3  OLT-1500001-01     A Coruña        5 hogares   1.3 h   92 %   8,8σ  · sustitución 100 %
run  24/24 detectados · 44 min antelación media · 0,0 % falsos positivos · señuelos 3/3
```

Regenerate: `curl -s "http://127.0.0.1:8001/api/runs/<run_id>/console?lang=es"`.

## Known limits

- The recording is **real time** — a full pass takes as long as the video.
- `record.mjs` clicks alerts **by entity id**, so if the seed changes those cards may not
  exist at the interval the script seeks to. It warns rather than failing silently.
- Segment `05-run` plays the ribbon at 8× to cover 576 intervals inside its narration.
