// Self-test for the live-transcript phrase splitting in voiceTurns.ts (no browser needed):
//   node --experimental-transform-types lib/voiceTurns.selftest.ts
// Feeds synthetic speech (noise bursts) and pauses through a stand-in AudioContext and checks
// that a long turn is sent phrase by phrase, in order, and that the turn ends as before.
import assert from "node:assert/strict";
import { VoiceTurnListener } from "./voiceTurns.ts";

const RATE = 48000, FRAME = 2048;
type Proc = { onaudioprocess: ((e: unknown) => void) | null; connect: () => void; disconnect: () => void };
let proc: Proc | null = null;
class FakeAudioContext {
  sampleRate = RATE; destination = {};
  createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
  createScriptProcessor() { proc = { onaudioprocess: null, connect() {}, disconnect() {} }; return proc; }
  close() { return Promise.resolve(); }
}
const g = globalThis as unknown as Record<string, unknown>;
g.window = { AudioContext: FakeAudioContext };
g.MediaStream = class {};

const sent: number[] = [];   // seconds of audio in each transcription request
const events: string[] = [];
const listener = new VoiceTurnListener(async (wav) => {
  sent.push(Math.round(((wav.size - 44) / 2 / 16000) * 10) / 10);
  return `phrase ${sent.length}`;
}, {
  onSpeechStart: () => events.push("start"),
  onTranscribing: () => events.push("transcribing"),
  onText: (t) => events.push(`${t}${listener.isSpeaking ? " (still speaking)" : ""}`),
  onError: (e) => { throw e; },
});
listener.start({ getAudioTracks: () => [] } as unknown as MediaStream);

let seed = 1;
const noise = () => ((seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5);
const feed = async (sec: number, amp: number) => {
  for (let i = 0; i < Math.round((sec * RATE) / FRAME); i++) {
    const frame = new Float32Array(FRAME).map(() => noise() * amp);
    proc!.onaudioprocess!({ inputBuffer: { getChannelData: () => frame } });
    await new Promise((r) => setImmediate(r));   // let queued transcriptions resolve, as in a browser
  }
};

await feed(0.6, 0.002);   // room calibration
await feed(4.0, 0.3);     // phrase 1 (4 s of speech)
await feed(0.7, 0.002);   // short pause → phrase 1 is sent while the turn continues
await feed(2.0, 0.3);     // phrase 2
await feed(2.0, 0.002);   // long silence → turn ends, phrase 2 sent
await feed(0.3, 0.002);
await new Promise((r) => setTimeout(r, 50));

assert.equal(sent.length, 2, `expected 2 requests, got ${sent.join(", ")}`);
assert.ok(sent[0] >= 4 && sent[0] <= 5.5, `phrase 1 should hold ~4 s, got ${sent[0]}`);
assert.deepEqual(events, ["start", "phrase 1 (still speaking)", "transcribing", "phrase 2"]);
assert.equal(listener.isBusy, false);

// A short turn (under the 3 s phrase minimum) is still sent once, at its end
sent.length = 0; events.length = 0;
await feed(2.0, 0.3);
await feed(2.0, 0.002);
await new Promise((r) => setTimeout(r, 50));
assert.equal(sent.length, 1);
assert.deepEqual(events, ["start", "transcribing", "phrase 1"]);

listener.stop();
console.log("voiceTurns self-test passed:", "phrase split at pauses, in order, turn end unchanged");
