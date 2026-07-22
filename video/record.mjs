/**
 * Records the demo: intro screen, the console walkthrough, the outro.
 *
 * The recording is one continuous Playwright video, not a series of clips, so there is
 * nothing to stitch and no risk of a seam landing mid-sentence. Screens (intro, the use
 * cases, outro) are a local HTML file styled from the same brand tokens as the console,
 * so the cut between them and the live app is invisible.
 *
 * TIMING. Each segment in narration.json carries a planned `seconds`. If the matching
 * mp3 exists in out/audio/, its real duration is used instead - so once the narration is
 * generated the visuals re-time themselves to the voice rather than the other way round.
 *
 * HIGHLIGHTING. `spotlight(selector)` dims the whole page and cuts a hole around the
 * element under discussion, using one overlay with a very large box-shadow. Nothing in
 * the app is cloned or moved, so what you see highlighted is the real component.
 *
 *   node record.mjs            # full run
 *   node record.mjs 06a-node   # one segment, for checking pacing before committing
 */

import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = process.env.APP_URL ?? 'http://127.0.0.1:8001/';
const OUT = path.join(HERE, 'out');
const AUDIO = path.join(OUT, 'audio');
const W = 1920;
const H = 1080;

const script = JSON.parse(fs.readFileSync(path.join(HERE, 'narration.json'), 'utf8'));
const only = process.argv[2] ?? null;

/** Real narration length when we have it, planned length until then. */
function secondsFor(seg) {
  const mp3 = path.join(AUDIO, `${seg.id}.mp3`);
  if (fs.existsSync(mp3)) {
    try {
      const out = execFileSync('ffprobe', [
        '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=nw=1:nk=1', mp3,
      ]).toString().trim();
      const d = parseFloat(out);
      // A beat of silence either side so a cut never clips the first syllable - and never
      // shorter than the planned length, because some segments are paced by the picture
      // rather than the voice: the title animation needs room to land, and the simulation
      // must run its full minute even though the narration over it is shorter.
      if (Number.isFinite(d) && d > 0) return Math.max(d + 0.9, seg.seconds);
    } catch { /* fall through to the planned length */ }
  }
  return seg.seconds;
}

const sleep = (s) => new Promise((r) => setTimeout(r, Math.max(0, s) * 1000));

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ args: ['--force-device-scale-factor=1'] });
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    recordVideo: { dir: OUT, size: { width: W, height: H } },
    deviceScaleFactor: 1,
    reducedMotion: 'no-preference',
  });
  const page = await context.newPage();

  // Recording starts HERE, not at the first segment: loading the app, switching to
  // Spanish and selecting the full network are all already being filmed. That lead has to
  // be measured, or the narration is laid over the setup and runs ahead of the picture
  // for the entire video.
  const tRecordingStart = Date.now();

  // ---- the app, prepared before anything is recorded in earnest ----
  await page.goto(APP, { waitUntil: 'networkidle', timeout: 60_000 });
  await page.waitForTimeout(2500);
  await page.locator('.seg button', { hasText: 'ES' }).click();
  await page.waitForTimeout(800);
  await page.locator('.seg button').filter({ hasText: 'Completa' }).click();
  // the full run is prewarmed server-side, but give the console a moment to render it
  await page.waitForSelector('.rail', { timeout: 60_000 });
  await page.waitForTimeout(6000);

  await installSpotlight(page);

  const screensUrl = 'file://' + path.join(HERE, 'screens.html');
  const segments = only ? script.segments.filter((s) => s.id === only) : script.segments;

  /**
   * When each segment actually began, in seconds from the first frame.
   *
   * The narration cannot be laid out by summing clip lengths: navigating to a screen,
   * seeking the timeline and clicking an alert all take real time that no clip accounts
   * for, and the error compounds - the first cut of this video ended with the voice 38
   * seconds ahead of the picture. So the recorder reports where each segment truly
   * landed and build.mjs places the audio there.
   */
  const t0 = Date.now();
  const timing = { leadSeconds: (t0 - tRecordingStart) / 1000, segments: [] };
  const stamp = (id) => timing.segments.push({ id, offset: (Date.now() - t0) / 1000 });

  for (const seg of segments) {
    const total = secondsFor(seg);
    stamp(seg.id);
    console.log(`  ${seg.id.padEnd(16)} ${total.toFixed(1)}s   @ ${((Date.now() - t0) / 1000).toFixed(1)}s`);

    if (seg.screen) {
      const alreadyOnScreens = page.url().startsWith('file://');
      if (!alreadyOnScreens) {
        await fade(page, true);
        await page.goto(screensUrl, { waitUntil: 'load' });
        await page.waitForTimeout(700);   // let the logo fetch land before revealing
        await installSpotlight(page);
      }
      await page.evaluate(({ id, plate }) => window.showScreen(id, plate),
                          { id: seg.screen, plate: seg.plate ?? '' });
      if (!alreadyOnScreens) await fade(page, false);

      if (seg.screen === 'usecases') {
        // The cards light in step with the narration: one intro beat, then a third of
        // what remains per card, so the highlight is always on the one being described.
        const intro = Math.min(9, total * 0.16);
        await sleep(intro);
        const per = (total - intro) / 3;
        for (const n of [1, 2, 3]) {
          await page.evaluate((k) => window.highlightUseCase(k), n);
          await sleep(per);
        }
      } else {
        await sleep(total);
      }
      continue;
    }

    // coming back to the console from a title screen
    if (page.url().startsWith('file://')) {
      await fade(page, true);
      await page.goto(APP, { waitUntil: 'networkidle' });
      await page.waitForTimeout(1000);
      await page.locator('.seg button', { hasText: 'ES' }).click();
      await page.locator('.seg button').filter({ hasText: 'Completa' }).click();
      await page.waitForTimeout(3200);
      await installSpotlight(page);
      await fade(page, false);
    }

    for (const a of seg.actions ?? []) await runAction(page, a);

    const beats = seg.beats ?? [{ at: 0, highlight: null }];
    for (let i = 0; i < beats.length; i++) {
      const b = beats[i];
      const until = i + 1 < beats.length ? beats[i + 1].at : total;
      await spotlight(page, b.highlight, b.label ?? null);
      await sleep(Math.max(0.4, until - b.at));
    }
    await spotlight(page, null, null);
  }

  timing.totalSeconds = (Date.now() - t0) / 1000;
  fs.writeFileSync(path.join(OUT, 'timing.json'), JSON.stringify(timing, null, 2));

  await page.waitForTimeout(500);
  await context.close();
  await browser.close();

  const produced = fs.readdirSync(OUT).filter((f) => f.endsWith('.webm'));
  console.log('\nwrote:', produced.map((f) => path.join('out', f)).join(', '));
}

/** Fade the picture down or up, so no cut is a hard jump. */
async function fade(page, down) {
  await page.evaluate((d) => {
    const f = document.getElementById('vid-fade');
    if (f) f.classList.toggle('on', d);
  }, down).catch(() => {});
  await page.waitForTimeout(620);
}

/** Inject the overlay once per page load. */
async function installSpotlight(page) {
  await page.addStyleTag({
    content: `
      #vid-spot {
        position: fixed; z-index: 99998; border-radius: 14px; pointer-events: none;
        box-shadow: 0 0 0 9999px rgba(4, 10, 18, 0.66), 0 0 0 2px #3c8dff,
                    0 0 34px rgba(60, 141, 255, 0.55);
        opacity: 0; transition: opacity .45s ease, top .5s ease, left .5s ease,
                    width .5s ease, height .5s ease;
      }
      #vid-spot.on { opacity: 1; }
      /* A lower third, not a chip pinned to the element: a caption that jumps around with
         the highlight reads as a debug overlay. This sits where a broadcast caption sits. */
      #vid-label {
        position: fixed; left: 56px; bottom: 104px; z-index: 99999; pointer-events: none;
        opacity: 0; transform: translateY(10px);
        transition: opacity .5s ease, transform .5s ease;
        background: linear-gradient(180deg, rgba(18,101,255,.96), rgba(10,46,115,.96));
        color: #fff; font-family: Arial, Helvetica, sans-serif;
        font-size: 19px; font-weight: 700; letter-spacing: .3px;
        padding: 13px 22px 13px 20px; border-radius: 10px;
        border-left: 4px solid #66b3ff;
        box-shadow: 0 18px 44px rgba(0,0,0,.55);
      }
      #vid-label.on { opacity: 1; transform: translateY(0); }
      #vid-fade {
        position: fixed; inset: 0; z-index: 100000; background: #050d17;
        opacity: 0; pointer-events: none; transition: opacity .55s ease;
      }
      #vid-fade.on { opacity: 1; }
    `,
  });
  await page.evaluate(() => {
    for (const id of ['vid-spot', 'vid-label', 'vid-fade']) {
      if (!document.getElementById(id)) {
        const d = document.createElement('div'); d.id = id; document.body.appendChild(d);
      }
    }
  });
}

async function spotlight(page, selector, label) {
  await page.evaluate(({ selector, label }) => {
    const spot = document.getElementById('vid-spot');
    const lab = document.getElementById('vid-label');
    if (!spot) return;
    if (!selector) { spot.classList.remove('on'); lab.classList.remove('on'); return; }
    const el = document.querySelector(selector);
    if (!el) { spot.classList.remove('on'); lab.classList.remove('on'); return; }
    const r = el.getBoundingClientRect();
    const pad = 8;
    spot.style.top = `${r.top - pad}px`;
    spot.style.left = `${r.left - pad}px`;
    spot.style.width = `${r.width + pad * 2}px`;
    spot.style.height = `${r.height + pad * 2}px`;
    spot.classList.add('on');
    if (label) { lab.textContent = label; lab.classList.add('on'); }
    else { lab.classList.remove('on'); }
  }, { selector, label });
}

async function runAction(page, a) {
  switch (a.do) {
    case 'seek':
      await page.locator('.scrub').evaluate((el, v) => {
        const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        set.call(el, String(v));
        el.dispatchEvent(new Event('input', { bubbles: true }));
      }, a.interval);
      await page.waitForTimeout(700);
      break;
    case 'play':
      await page.locator('.play').click(); await page.waitForTimeout(300); break;
    case 'pause': {
      const playing = await page.locator('.play svg').getAttribute('data-icon').catch(() => null);
      await page.locator('.play').click().catch(() => {});
      await page.waitForTimeout(300);
      break;
    }
    case 'speed': {
      // cycle the speed button until it reads the requested multiplier
      for (let i = 0; i < 5; i++) {
        const txt = (await page.locator('.speed').textContent()) ?? '';
        if (txt.trim().startsWith(String(a.value))) break;
        await page.locator('.speed').click();
        await page.waitForTimeout(150);
      }
      break;
    }
    case 'tab': {
      const names = { analista: 'Analista', direccion: 'Dirección', mapa: 'Mapa' };
      await page.locator('.tabs button', { hasText: names[a.name] }).click();
      await page.waitForTimeout(900);
      break;
    }
    case 'clickAlertByEntity': {
      const card = page.locator('.queue button', { hasText: a.entity }).first();
      if (await card.count()) { await card.click(); await page.waitForTimeout(900); }
      else console.warn(`    ! no alert card for ${a.entity} at this interval`);
      break;
    }
    default:
      console.warn('    ! unknown action', a.do);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
