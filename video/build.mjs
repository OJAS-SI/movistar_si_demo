/**
 * Composites the final video: the screen recording plus the narration track.
 *
 * The segments are concatenated in narration.json order with the same 0.45s of lead-in
 * that record.mjs holds before each segment starts, so speech and visuals stay in step
 * across the whole run rather than drifting after the first long section.
 *
 *   node build.mjs
 *   -> out/movistar-si-demo-es.mp4
 */

import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'out');
const AUDIO = path.join(OUT, 'audio');
const LEAD = 0.45;   // must match the padding record.mjs adds around each segment

const script = JSON.parse(fs.readFileSync(path.join(HERE, 'narration.json'), 'utf8'));
const ff = (args) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args], { stdio: 'inherit' });
const probe = (f) =>
  parseFloat(execFileSync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f,
  ]).toString().trim());

const webms = fs.readdirSync(OUT).filter((f) => f.endsWith('.webm'));
if (!webms.length) { console.error('No recording in out/. Run: node record.mjs'); process.exit(1); }
if (webms.length > 1) console.warn(`  ${webms.length} recordings present; using the newest.`);
const video = path.join(OUT, webms
  .map((f) => ({ f, t: fs.statSync(path.join(OUT, f)).mtimeMs }))
  .sort((a, b) => b.t - a.t)[0].f);

// ---- narration track: silence, then each clip at the offset its segment starts ----
const missing = script.segments.filter((s) => !fs.existsSync(path.join(AUDIO, `${s.id}.mp3`)));
if (missing.length) {
  console.error('Missing narration for:', missing.map((s) => s.id).join(', '));
  console.error('Run: ELEVENLABS_API_KEY=sk_... node tts.mjs');
  process.exit(1);
}

// Where each segment really started, measured during the recording. Summing clip
// lengths instead would drift by the time every navigation and click takes.
const timingPath = path.join(OUT, 'timing.json');
if (!fs.existsSync(timingPath)) {
  console.error('No out/timing.json - re-run record.mjs (it now records segment offsets).');
  process.exit(1);
}
const timing = JSON.parse(fs.readFileSync(timingPath, 'utf8'));
const offsetOf = Object.fromEntries(timing.segments.map((s) => [s.id, s.offset]));

// Everything before the first segment is the app being set up; trim it off the front.
// `leadSeconds` is measured by the recorder. Takes made before that existed are still
// usable: the lead is whatever the video has that the segment clock does not, less the
// half-second the recorder holds at the end.
const videoSeconds = probe(video);
const lead = timing.leadSeconds ?? Math.max(0, videoSeconds - timing.totalSeconds - 0.6);
const trim = Math.max(0, lead + (offsetOf[script.segments[0].id] ?? 0) - 0.4);
if (timing.leadSeconds === undefined) {
  console.log(`  lead derived as ${lead.toFixed(1)}s (take predates leadSeconds)`);
}

const inputs = [];
const filters = [];
script.segments.forEach((seg, i) => {
  const clip = path.join(AUDIO, `${seg.id}.mp3`);
  const at = Math.max(0, (offsetOf[seg.id] ?? 0) - trim + LEAD);
  inputs.push('-i', clip);
  filters.push(`[${i}:a]adelay=${Math.round(at * 1000)}|${Math.round(at * 1000)}[a${i}]`);
});
const mixed = path.join(OUT, 'narration.m4a');
ff([
  ...inputs,
  '-filter_complex',
  `${filters.join(';')};${script.segments.map((_, i) => `[a${i}]`).join('')}amix=inputs=${script.segments.length}:dropout_transition=0:normalize=0[out]`,
  '-map', '[out]', '-c:a', 'aac', '-b:a', '192k', mixed,
]);

const vDur = videoSeconds - trim;
const aDur = probe(mixed);
console.log(`  trimmed ${trim.toFixed(1)}s of setup`);
console.log(`  video ${vDur.toFixed(1)}s   narration ends ${aDur.toFixed(1)}s`);
if (aDur > vDur + 2) console.warn('  NOTE: narration outlasts the picture - lengthen the last segment.');

const final = path.join(OUT, 'movistar-si-demo-es.mp4');
ff([
  '-ss', String(trim), '-i', video, '-i', mixed,
  '-map', '0:v:0', '-map', '1:a:0',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p',
  '-r', '30', '-movflags', '+faststart',
  '-c:a', 'aac', '-b:a', '192k',
  '-shortest', final,
]);

const mins = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
console.log(`\n  ${path.relative(process.cwd(), final)}  ${mins(probe(final))}  ${(fs.statSync(final).size / 1e6).toFixed(1)} MB`);
