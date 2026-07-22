/**
 * Narration: one mp3 per segment of narration.json, via ElevenLabs.
 *
 * Per segment rather than one long file, because record.mjs times the visuals from each
 * clip's real duration - so the spotlight moves when the sentence about it is actually
 * spoken, without anyone hand-tuning offsets.
 *
 * The key is read from ELEVENLABS_API_KEY and never written to disk here.
 *
 *   ELEVENLABS_API_KEY=sk_... node tts.mjs          # only what is missing
 *   ELEVENLABS_API_KEY=sk_... node tts.mjs --force  # regenerate everything
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const AUDIO = path.join(HERE, 'out', 'audio');

const KEY = process.env.ELEVENLABS_API_KEY;
const VOICE = process.env.ELEVENLABS_VOICE ?? 'dNjJKg63Fr5AXwIdkATa';
const MODEL = process.env.ELEVENLABS_MODEL ?? 'eleven_multilingual_v2';
const FORCE = process.argv.includes('--force');

if (!KEY) {
  console.error('ELEVENLABS_API_KEY is not set.');
  process.exit(1);
}

const script = JSON.parse(fs.readFileSync(path.join(HERE, 'narration.json'), 'utf8'));
fs.mkdirSync(AUDIO, { recursive: true });

const duration = (f) =>
  parseFloat(execFileSync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f,
  ]).toString().trim());

let planned = 0;
let actual = 0;

for (const seg of script.segments) {
  const out = path.join(AUDIO, `${seg.id}.mp3`);
  planned += seg.seconds;

  if (fs.existsSync(out) && !FORCE) {
    const d = duration(out);
    actual += d;
    console.log(`  ${seg.id.padEnd(16)} cached   ${d.toFixed(1)}s`);
    continue;
  }

  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}`, {
    method: 'POST',
    headers: { 'xi-api-key': KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: seg.text,
      model_id: MODEL,
      // Stability a little above default keeps a long technical read even; the style
      // knob stays at zero because this is narration, not performance.
      voice_settings: { stability: 0.45, similarity_boost: 0.75, style: 0.0, use_speaker_boost: true },
    }),
  });

  if (!res.ok) {
    console.error(`  ${seg.id}: HTTP ${res.status} ${(await res.text()).slice(0, 200)}`);
    process.exit(1);
  }

  fs.writeFileSync(out, Buffer.from(await res.arrayBuffer()));
  const d = duration(out);
  actual += d;
  const drift = d - seg.seconds;
  const flag = Math.abs(drift) > 4 ? '  <-- differs from plan' : '';
  console.log(`  ${seg.id.padEnd(16)} ${d.toFixed(1)}s (plan ${seg.seconds}s, ${drift >= 0 ? '+' : ''}${drift.toFixed(1)})${flag}`);
}

const mins = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
console.log(`\n  planned ${mins(planned)}   spoken ${mins(actual)}`);
if (actual > 330) console.log('  NOTE: over 5:30 - trim narration.json before recording.');
