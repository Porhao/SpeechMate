"use client";
/* eslint-disable @typescript-eslint/no-explicit-any -- MediaPipe handles have no bundled types */
// Self-contained parts of the live session: the mic level meter and the camera's face/pose tracking.
// Turn-taking (speech-to-text, the AI's reply, its voice) stays in page.tsx, where its refs live.

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import type { FaceBox } from "@/lib/lighting";
import { MOOD_STATES, clamp, ema, inferMood, type Blendshape, type MoodLabel } from "./script";

export type MpStatus = "idle" | "loading" | "ready" | "error";
type Mood = { label: MoodLabel; score: number };

// ── Live audio metering ────────────────────────────────────────────────────────
// Real mic amplitude driving the orb and the level bar, not a canned animation. `audioLevel` is a
// throttled (~12 Hz) copy of a smoothed per-frame level, for React-rendered elements.
export function useAudioMeter() {
  const ctxRef = useRef<AudioContext | null>(null);
  const levelRef = useRef(0);
  const rafRef = useRef(0);
  const [audioLevel, setAudioLevel] = useState(0);

  const start = useCallback((stream: MediaStream) => {
    try {
      const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AC();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.55;
      ctx.createMediaStreamSource(stream).connect(analyser);
      ctxRef.current = ctx;

      const data = new Uint8Array(analyser.frequencyBinCount);
      let lastUi = 0;
      const tick = () => {
        analyser.getByteFrequencyData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i];
        levelRef.current = levelRef.current * 0.72 + (sum / data.length / 255) * 0.28;
        const now = performance.now();
        if (now - lastUi > 80) { setAudioLevel(levelRef.current); lastUi = now; }
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch { /* audio metering is a nice-to-have, session still works without it */ }
  }, []);

  const stop = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    ctxRef.current?.close().catch(() => {});
    ctxRef.current = null;
    levelRef.current = 0; setAudioLevel(0);
  }, []);

  return { audioLevel, start, stop };
}

// ── Face and pose tracking (MediaPipe, in the browser) ─────────────────────────
// Draws the face mesh, a mood tag and the pose skeleton on `canvasRef` over `videoRef`, while
// `activeRef` is true. `onTick` runs every ~500 ms (the page updates its live pace there).
export function useFaceTracking(
  videoRef: RefObject<HTMLVideoElement | null>,
  canvasRef: RefObject<HTMLCanvasElement | null>,
  activeRef: RefObject<boolean>,
  onTick: (now: number) => void,
) {
  const [mpStatus, setMpStatus] = useState<MpStatus>("idle");
  const [faceDetected, setFaceDetected] = useState(false);
  const [poseDetected, setPoseDetected] = useState(false);
  const [mood, setMood] = useState<Mood | null>(null);
  const mpRef = useRef<any>(null);
  const animRef = useRef(0);
  const lastTsRef = useRef(0);
  const lastUpdateRef = useRef(0);
  const moodRef = useRef<Mood | null>(null);
  // Face box in normalised frame coordinates, for the lighting check
  const faceNormRef = useRef<FaceBox | null>(null);
  const onTickRef = useRef(onTick);
  useEffect(() => { onTickRef.current = onTick; }, [onTick]);

  const init = useCallback(async () => {
    if (mpRef.current) return;
    setMpStatus("loading");
    try {
      const { FaceLandmarker, PoseLandmarker, FilesetResolver, DrawingUtils } = await import("@mediapipe/tasks-vision");
      // The WASM must be the same version as the JS package (pinned exactly in package.json)
      const vision = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm");
      const [fl, pl] = await Promise.all([
        FaceLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task", delegate: "GPU" },
          outputFaceBlendshapes: true, runningMode: "VIDEO", numFaces: 1,
        }),
        PoseLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task", delegate: "GPU" },
          runningMode: "VIDEO", numPoses: 1,
        }),
      ]);
      mpRef.current = { faceLandmarker: fl, poseLandmarker: pl, FaceLandmarker, PoseLandmarker, DrawingUtils };
      setMpStatus("ready");
    } catch { setMpStatus("error"); }
  }, []);

  // FaceLandmarker/PoseLandmarker each hold a WASM instance and a GPU delegate that outlive the JS
  // object: leaving them to garbage collection leaked a GPU context per session navigated away from.
  const dispose = useCallback(() => {
    const mp = mpRef.current;
    if (!mp) return;
    try { mp.faceLandmarker?.close(); } catch { /* already gone */ }
    try { mp.poseLandmarker?.close(); } catch { /* already gone */ }
    mpRef.current = null;
  }, []);

  /** One frame: detect, draw, and every ~500 ms publish the mood and call onTick. */
  const detect = useCallback(() => {
    const video = videoRef.current, canvas = canvasRef.current, mp = mpRef.current;
    const now = performance.now();
    if (mp && video && canvas && video.readyState >= 2 && video.videoWidth > 0 && now > lastTsRef.current) {
      const w = canvas.parentElement?.offsetWidth ?? video.videoWidth;
      const h = canvas.parentElement?.offsetHeight ?? video.videoHeight;
      if (canvas.width !== w) canvas.width = w;
      if (canvas.height !== h) canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.clearRect(0, 0, w, h); lastTsRef.current = now;
        if (!mp._du) mp._du = new mp.DrawingUtils(ctx);
        const du = mp._du;
        try {
          const fr = mp.faceLandmarker.detectForVideo(video, now);
          if (fr.faceLandmarks.length > 0) {
            setFaceDetected(true); const fl = fr.faceLandmarks[0];
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_TESSELATION, { color: "#FFFFFF10", lineWidth: 0.4 });
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE, { color: "#00E5FF", lineWidth: 1.5 });
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_LEFT_EYE,  { color: "#00E5FF", lineWidth: 1.5 });
            du.drawConnectors(fl, mp.FaceLandmarker.FACE_LANDMARKS_LIPS, { color: "#FF804060", lineWidth: 1 });

            // Mood, inferred from the same detector's blendshape output
            const shapes = fr.faceBlendshapes?.[0]?.categories as Blendshape[] | undefined;
            if (shapes?.length) {
              const next = inferMood(shapes);
              const smoothedScore = moodRef.current?.label === next.label
                ? Math.round(ema(moodRef.current.score, next.score, 0.2))
                : next.score;
              moodRef.current = { label: next.label, score: smoothedScore };
            }

            // Face bounding box (canvas pixel space) for the overlay tag
            let minX = 1, minY = 1, maxX = 0, maxY = 0;
            for (const p of fl) {
              if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
              if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
            }
            const pad = 0.04;
            const bx = clamp((minX - pad) * w, 0, w), by = clamp((minY - pad * 1.4) * h, 0, h);
            const bw = clamp((maxX - minX + pad * 2) * w, 0, w - bx), bh = clamp((maxY - minY + pad * 2.4) * h, 0, h - by);
            faceNormRef.current = { x: minX, y: minY, w: maxX - minX, h: maxY - minY };

            // Bracket-corner box + mood tag, like a HUD-style ID overlay
            if (moodRef.current) {
              const mc2 = MOOD_STATES[moodRef.current.label].color;
              const corner = Math.min(18, bw * 0.18, bh * 0.18);
              ctx.strokeStyle = `${mc2}CC`; ctx.lineWidth = 1.6; ctx.lineCap = "round";
              const drawCorner = (cx: number, cy: number, dx: number, dy: number) => {
                ctx.beginPath();
                ctx.moveTo(cx, cy + dy * corner); ctx.lineTo(cx, cy); ctx.lineTo(cx + dx * corner, cy);
                ctx.stroke();
              };
              drawCorner(bx, by, 1, 1);
              drawCorner(bx + bw, by, -1, 1);
              drawCorner(bx, by + bh, 1, -1);
              drawCorner(bx + bw, by + bh, -1, -1);

              const label = `${moodRef.current.label} · ${moodRef.current.score}%`;
              ctx.font = "600 11px Inter, sans-serif";
              const tw = ctx.measureText(label).width;
              const tagX = clamp(bx, 0, w - tw - 16), tagY = Math.max(0, by - 22);
              ctx.fillStyle = `${mc2}E6`;
              ctx.beginPath();
              ctx.roundRect?.(tagX, tagY, tw + 16, 20, 6);
              ctx.fill();
              ctx.fillStyle = "#FFFFFF";
              ctx.fillText(label, tagX + 8, tagY + 14);
            }
          } else { setFaceDetected(false); faceNormRef.current = null; }
        } catch { /* transient */ }
        try {
          const pr = mp.poseLandmarker.detectForVideo(video, now);
          if (pr.landmarks.length > 0) {
            setPoseDetected(true); const pl = pr.landmarks[0];
            du.drawConnectors(pl, mp.PoseLandmarker.POSE_CONNECTIONS, { color: "#5C729B60", lineWidth: 2.5 });
            du.drawLandmarks(pl.slice(0, 25), { color: "#60EFFF", fillColor: "#1060FF80", radius: 3 });
          } else { setPoseDetected(false); }
        } catch { /* transient */ }
      }
    }
    if (now - lastUpdateRef.current > 500) {
      onTickRef.current(now);
      setMood(moodRef.current);
      lastUpdateRef.current = now;
    }
  }, [videoRef, canvasRef]);

  /** Load the models (once) and start tracking, if the session is still active by then. */
  const start = useCallback(() => {
    lastTsRef.current = 0; lastUpdateRef.current = 0;
    const loop = () => {
      if (!activeRef.current) return;
      detect();
      animRef.current = requestAnimationFrame(loop);
    };
    init().then(() => { if (activeRef.current) animRef.current = requestAnimationFrame(loop); });
  }, [init, detect, activeRef]);

  const stop = useCallback(() => cancelAnimationFrame(animRef.current), []);

  return { mpStatus, faceDetected, poseDetected, mood, faceNormRef, start, stop, dispose };
}
