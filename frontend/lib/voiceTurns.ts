// Voice-turn capture for the live AI conversation.
//
// Instead of the browser's speech recogniser (weak on Malaysian English and
// Chrome-only), this listens to the mic stream, finds each spoken turn with a
// simple energy-based voice activity detector (adaptive to the room's noise
// floor), keeps ~0.35 s of audio from just before speech started so the first
// word isn't clipped, and hands the turn to `transcribe` as a 16 kHz mono WAV —
// the backend runs faster-whisper on it.

const TARGET_RATE = 16000;
const FRAME_SIZE = 2048;             // ≈ 43 ms at 48 kHz
const PREROLL_SEC = 0.35;
const END_SILENCE_SEC = 1.0;         // this much quiet ends the turn
const MIN_SPEECH_SEC = 0.35;         // shorter blips (a cough, a click) are ignored
const MAX_TURN_SEC = 30;
const START_FRAMES = 3;              // consecutive loud frames needed to start a turn
const MIN_THRESHOLD = 0.012;         // RMS floor, so a silent room isn't "speech"
const NOISE_MULTIPLIER = 3;

export interface VoiceTurnCallbacks {
  onSpeechStart: () => void;
  onTranscribing: () => void;
  onText: (text: string) => void;       // may be "" when the turn held no words
  onError: (error: Error) => void;
}

export class VoiceTurnListener {
  private ctx: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private node: ScriptProcessorNode | null = null;
  private stopped = false;

  private noiseFloor = 0.005;
  private calibrationFrames = 0;
  private loudRun = 0;
  private quietSec = 0;
  private speaking = false;
  private preroll: Float32Array[] = [];
  private turn: Float32Array[] = [];
  private turnSec = 0;
  private speechSec = 0;
  private queue: Promise<void> = Promise.resolve();  // keeps turns in the order they were spoken

  constructor(
    private readonly transcribe: (wav: Blob) => Promise<string>,
    private readonly cb: VoiceTurnCallbacks,
  ) {}

  start(stream: MediaStream) {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    this.ctx = new AC();
    this.source = this.ctx.createMediaStreamSource(new MediaStream(stream.getAudioTracks()));
    this.node = this.ctx.createScriptProcessor(FRAME_SIZE, 1, 1);
    const frameSec = FRAME_SIZE / this.ctx.sampleRate;
    const prerollFrames = Math.ceil(PREROLL_SEC / frameSec);

    this.node.onaudioprocess = (e) => {
      if (this.stopped) return;
      const frame = new Float32Array(e.inputBuffer.getChannelData(0));
      let sum = 0;
      for (let i = 0; i < frame.length; i++) sum += frame[i] * frame[i];
      const rms = Math.sqrt(sum / frame.length);

      // Learn the room's noise level from the first ~0.5 s, then keep adapting while quiet
      if (this.calibrationFrames < 12) {
        this.noiseFloor = this.calibrationFrames === 0 ? rms : this.noiseFloor * 0.8 + rms * 0.2;
        this.calibrationFrames++;
        return;
      }
      const threshold = Math.max(this.noiseFloor * NOISE_MULTIPLIER, MIN_THRESHOLD);
      const loud = rms > threshold;

      if (!this.speaking) {
        this.noiseFloor = loud ? this.noiseFloor : this.noiseFloor * 0.95 + rms * 0.05;
        this.preroll.push(frame);
        if (this.preroll.length > prerollFrames) this.preroll.shift();
        this.loudRun = loud ? this.loudRun + 1 : 0;
        if (this.loudRun >= START_FRAMES) {
          this.speaking = true;
          this.turn = [...this.preroll];
          this.turnSec = this.turn.length * frameSec;
          this.speechSec = this.loudRun * frameSec;
          this.quietSec = 0;
          this.preroll = [];
          this.cb.onSpeechStart();
        }
        return;
      }

      this.turn.push(frame);
      this.turnSec += frameSec;
      if (rms > threshold * 0.7) { this.quietSec = 0; this.speechSec += frameSec; }
      else this.quietSec += frameSec;
      if (this.quietSec >= END_SILENCE_SEC || this.turnSec >= MAX_TURN_SEC) this.endTurn();
    };

    this.source.connect(this.node);
    // A ScriptProcessor only runs while connected to the output; it writes silence there
    this.node.connect(this.ctx.destination);
  }

  private endTurn() {
    const frames = this.turn;
    const speechSec = this.speechSec;
    this.speaking = false;
    this.turn = []; this.turnSec = 0; this.speechSec = 0; this.loudRun = 0; this.quietSec = 0;
    if (speechSec < MIN_SPEECH_SEC || !this.ctx) return;

    const wav = encodeWav(resample(concat(frames), this.ctx.sampleRate, TARGET_RATE), TARGET_RATE);
    this.cb.onTranscribing();
    this.queue = this.queue.then(async () => {
      try {
        const text = (await this.transcribe(wav)).trim();
        if (!this.stopped) this.cb.onText(text);  // "" = nothing intelligible was said
      } catch (e) {
        if (!this.stopped) this.cb.onError(e instanceof Error ? e : new Error(String(e)));
      }
    });
  }

  /** Stop listening. A turn still being spoken is dropped; turns already sent are ignored. */
  stop() {
    this.stopped = true;
    if (this.node) this.node.onaudioprocess = null;
    try { this.source?.disconnect(); this.node?.disconnect(); } catch { /* already disconnected */ }
    this.ctx?.close().catch(() => {});
    this.ctx = null; this.source = null; this.node = null;
  }
}

function concat(frames: Float32Array[]): Float32Array {
  const out = new Float32Array(frames.reduce((n, f) => n + f.length, 0));
  let offset = 0;
  for (const f of frames) { out.set(f, offset); offset += f.length; }
  return out;
}

/** Linear-interpolation resample (48 kHz → 16 kHz for Whisper). */
function resample(input: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const pos = i * ratio;
    const i0 = Math.floor(pos);
    const i1 = Math.min(i0 + 1, input.length - 1);
    out[i] = input[i0] + (input[i1] - input[i0]) * (pos - i0);
  }
  return out;
}

/** 16-bit PCM mono WAV. */
function encodeWav(samples: Float32Array, rate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buffer);
  const str = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], { type: "audio/wav" });
}
