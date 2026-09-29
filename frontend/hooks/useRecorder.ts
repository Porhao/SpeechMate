"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return MIME_CANDIDATES.find((t) => MediaRecorder.isTypeSupported(t));
}

/** Microphone recorder: start/stop/reset, with the result as a Blob + object URL. */
export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanupStream = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  };

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = pickMimeType();
      const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = () => {
        const out = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        setBlob(out);
        setUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(out); });
        cleanupStream();
        setRecording(false);
      };
      recorderRef.current = rec;
      rec.start(250);
      setSeconds(0);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
      setRecording(true);
    } catch (e) {
      cleanupStream();
      setError(e instanceof Error && e.name === "NotAllowedError"
        ? "Microphone access was blocked. Allow it in your browser and try again."
        : "Couldn't start the microphone.");
    }
  }, []);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  const reset = useCallback(() => {
    stop();
    setBlob(null);
    setUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
    setSeconds(0);
  }, [stop]);

  useEffect(() => () => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    cleanupStream();
  }, []);

  return { recording, blob, url, seconds, error, start, stop, reset };
}
