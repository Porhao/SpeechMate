"use client";

import { Suspense, useEffect, useRef, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Mic, MicOff, PhoneOff, Send, Volume2, VolumeX, Shuffle,
  Activity, Loader2, Video, VideoOff, Briefcase, Presentation, ListChecks, Keyboard,
} from "lucide-react";
import { cn, inkOf } from "@/lib/utils";
import { liveService, conversationService } from "@/services/live";
import { api, ApiError } from "@/services/api";
import { VoiceTurnListener } from "@/lib/voiceTurns";
import SlideImage from "@/components/presentation/SlideImage";
import { analyzeLighting, type LightingReport } from "@/lib/lighting";
import type { SessionType, LiveSession } from "@/types";
import { formatDuration } from "@/lib/format";
import { isSessionType, MODES } from "@/lib/modes";
import {
  BACKCHANNEL_TEXTS, CHECKIN_MESSAGES, MODE_ACKS, MODE_PROMPTS, MOOD_STATES, RANDOM_TOPICS,
  paceWpm, type MoodLabel,
} from "./script";
import { POSTURE_TIPS, useAudioMeter, useFaceTracking } from "./hooks";
import { HeaderPulse, LiveTranscript, PartnerBot, UserBubble, VoiceBeam, VolumeMeter, type OrbState } from "./widgets";

// ── Types ─────────────────────────────────────────────────────────────────────
type Message  = { role: "ai" | "user"; text: string; ts: number };

// ── Session ───────────────────────────────────────────────────────────────────
function SessionContent() {
  const searchParams = useSearchParams();
  const router       = useRouter();
  // A session prepared beforehand (interview setup / deck Q&A) arrives as ?live=<id>&mode=…
  const liveParam    = searchParams.get("live");
  const modeParam    = searchParams.get("mode");
  const mode: SessionType = isSessionType(modeParam) ? modeParam : "Conversation";

  // Off until the camera really starts, so a permission error shows in its place
  const [isRecording, setRecording] = useState(false);
  const [isCameraOn, setCameraOn] = useState(false);
  const [duration, setDuration] = useState(0);
  const [transcript, setTranscript] = useState("");  // the user's words so far, shown live
  const appendTranscript = useCallback((text: string) => setTranscript((t) => (t ? `${t} ${text}` : text)), []);

  // ── State ─────────────────────────────────────────────────────────────────
  const [sessionStarted, setSessionStarted] = useState(false);
  const [messages,       setMessages]       = useState<Message[]>([]);
  const [input,          setInput]          = useState("");
  const [aiTyping,       setAiTyping]       = useState(false);
  const [aiSpeaking,     setAiSpeaking]     = useState(false);
  const [isEnding,       setIsEnding]       = useState(false);
  // true while the mic is open for the user's turn (not tied to the recogniser's internal restarts)
  const [speechActive,   setSpeechActive]   = useState(false);
  // Camera's real aspect ratio, so the tracking inset shows the full frame and the
  // landmark overlay (drawn in normalised frame coordinates) lines up exactly
  const [camAspect,      setCamAspect]      = useState("16 / 9");
  const [lighting,       setLighting]       = useState<LightingReport | null>(null);
  // AI reply text is ready and its voice is loading: shown as "thinking" until audio really plays
  const [voicePending,   setVoicePending]   = useState(false);
  const [interimText,    setInterimText]    = useState("");
  const [newestPhrase,   setNewestPhrase]   = useState<{ text: string; key: number } | null>(null);
  // Presentation talk: the slide on screen, and when each slide was put up (seconds into the recording)
  const [slideIdx, setSlideIdx] = useState(1);
  const [showCue, setShowCue] = useState(false);
  const slideTimesRef = useRef<{ slide_index: number; t_sec: number }[]>([]);
  const recStartRef = useRef(0);
  const isTalkRef = useRef(false);
  const slideIdxRef = useRef(1);
  const slideCountRef = useRef(0);
  // Move to slide n (clamped); while presenting, note when it went up
  const goToSlide = (n: number) => {
    const next = Math.max(1, Math.min(slideCountRef.current, n));
    if (!slideCountRef.current || next === slideIdxRef.current) return;
    slideIdxRef.current = next;
    setSlideIdx(next);
    if (activeRef.current && recStartRef.current) {
      slideTimesRef.current.push({ slide_index: next, t_sec: Math.round((Date.now() - recStartRef.current) / 100) / 10 });
    }
  };
  // Words already transcribed and waiting for the AI's reply (shows "I'm done, reply now")
  const [pendingSpeech,  setPendingSpeech]  = useState(false);
  const replyAsapRef = useRef(false);           // the user pressed "reply now": skip the wait
  const replyWhenQuietRef = useRef<() => void>(() => {});
  // Why the camera/mic couldn't start (permission denied, no device, in use elsewhere)
  const [camError,       setCamError]       = useState<string | null>(null);
  const [startError,     setStartError]     = useState<string | null>(null);  // the session couldn't be created
  const [wpm,            setWpm]            = useState(0);
  const [voiceEnabled,   setVoiceEnabled]   = useState(true);
  const [currentTopic,   setCurrentTopic]   = useState(searchParams.get("topic") || RANDOM_TOPICS[0]);
  // A drill from the results page ("Practise this now"): the one skill to focus on, kept on screen
  const drillFocus = searchParams.get("focus");

  // The prepared session (interview setup / deck) and how far through its question plan we are
  const [prepared,      setPrepared]      = useState<LiveSession | null>(null);
  const [planProgress,  setPlanProgress]  = useState<{ asked: number; total: number } | null>(null);

  // ── DOM refs ─────────────────────────────────────────────────────────────
  // Two views of the same camera stream: a large clean "mirror" (videoRef, which
  // MediaPipe reads from) and a small tracking inset with the landmark overlay
  const videoRef      = useRef<HTMLVideoElement>(null);
  const trackVideoRef = useRef<HTMLVideoElement>(null);
  const canvasRef     = useRef<HTMLCanvasElement>(null);
  const streamRef  = useRef<MediaStream | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  // Speech-to-text for the user's turns is the backend's (cloud Whisper, e.g. Groq).
  // No browser fallback: Chrome's recogniser sends audio to Google and is English-only
  // (fine-tune/docs/manglish-transcription-spec.md). Without a backend model the user types instead.
  const [sttAvailable,   setSttAvailable]   = useState(true);
  const sttAvailableRef  = useRef(true);
  const sttFailsRef      = useRef(0);  // consecutive failed transcriptions
  const [sttNotice,      setSttNotice]      = useState("");
  const voiceListenerRef = useRef<VoiceTurnListener | null>(null);
  const mediaRecorderRef    = useRef<MediaRecorder | null>(null);
  const recordedChunksRef   = useRef<Blob[]>([]);
  const backendSessionIdRef = useRef<string | null>(null);

  // What the user is answering, sent with each turn so speech recognition gets topic words right
  const sttContextRef = useRef("");

  // ── Value refs ────────────────────────────────────────────────────────────
  const activeRef           = useRef(false);
  const aiTypingRef         = useRef(false);
  const aiSpeakingRef       = useRef(false);
  const voiceEnabledRef     = useRef(true);
  const isRecordingRef      = useRef(false);
  const modeRef             = useRef(mode);  // from the URL: fixed for the page's life
  // Response time: from the end of the AI's turn to the first sound of the user's answer
  const turnOpenedAtRef     = useRef<number | null>(null);
  const latenciesRef        = useRef<number[]>([]);
  const sessionStartedAtRef = useRef(0);
  const wordListRef         = useRef<string[]>([]);
  const startTimeRef        = useRef(0);
  const lastSpeechTimeRef   = useRef(0);
  const checkinAskedRef     = useRef(false);
  const silenceCheckRef     = useRef<ReturnType<typeof setInterval> | null>(null);
  const startSpeechRef      = useRef<() => void>(() => {});
  const promptIndexRef      = useRef(0);
  const pendingUserSpeechRef = useRef("");
  const autoReplyTimerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const triggerAIReplyRef   = useRef<(t: string) => void | Promise<void>>(() => {});

  // Audio seconds of every turn sent to speech recognition (each is billed ≥ 10 s): session usage
  const sttAudioSecRef      = useRef<number[]>([]);

  // Backchannel refs
  const backchannelUrlsRef  = useRef<string[]>([]);
  const lastBackchannelRef  = useRef(0);
  const backchannelTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const backchannelAudioRef = useRef<HTMLAudioElement | null>(null);

  // Audio ref (main TTS)
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Bumped for every AI utterance; callbacks from an older (cancelled) utterance are ignored
  const speakTokenRef = useRef(0);

  // Track conversation history for real AI calls
  const messagesRef     = useRef<Message[]>([]);
  const replyGenRef     = useRef(0);
  const currentTopicRef = useRef(currentTopic);

  // ── Mic level and face/pose tracking (hooks.ts) ──────────────────────────
  const { audioLevel, start: startMeter, stop: stopMeter } = useAudioMeter();
  const { mpStatus, faceDetected, poseDetected, mood, postureTip, faceNormRef,
          start: startTracking, stop: stopTracking, dispose: disposeTracking } =
    useFaceTracking(videoRef, canvasRef, activeRef,
      (now) => setWpm(paceWpm(wordListRef.current.length, (now - startTimeRef.current) / 1000)));

  // ── Sync refs ─────────────────────────────────────────────────────────────
  useEffect(() => { aiTypingRef.current      = aiTyping; },       [aiTyping]);
  useEffect(() => { voiceEnabledRef.current  = voiceEnabled; },   [voiceEnabled]);
  useEffect(() => { isRecordingRef.current   = isRecording; },    [isRecording]);
  useEffect(() => { messagesRef.current      = messages; },       [messages]);
  useEffect(() => { currentTopicRef.current  = currentTopic; },   [currentTopic]);

  // ── TFLite log suppression ────────────────────────────────────────────────
  useEffect(() => {
    const orig = console.error.bind(console);
    console.error = (...a: unknown[]) => {
      const s = String(a[0] ?? "");
      if (s.includes("TensorFlow Lite") || s.includes("XNNPACK") || s.startsWith("INFO:")) return;
      orig(...a);
    };
    return () => { console.error = orig; };
  }, []);

  // ── Turn-taking ───────────────────────────────────────────────────────────
  // listening → thinking (LLM) → thinking (voice loading) → speaking → listening.
  // The mic is fully closed (recogniser detached) while it's the AI's turn, so the
  // AI never hears itself and no late recogniser event can reopen or double it.
  const detachRecognizer = useCallback(() => {
    voiceListenerRef.current?.stop();
    voiceListenerRef.current = null;
    // The session recording (sent for analysis) only keeps the user's turns: AI turns
    // would otherwise count as long pauses and stutter "blocks" in the user's speech
    const mr = mediaRecorderRef.current;
    if (mr?.state === "recording") { try { mr.pause(); } catch { /* unsupported */ } }
    setSpeechActive(false); setInterimText("");
  }, []);

  const resumeListening = useCallback(() => {
    // The user's turn starts now: the "still there?" check-in counts silence from here, not
    // from before the AI's (possibly slow) reply, which made it fire as soon as the AI stopped
    lastSpeechTimeRef.current = Date.now();
    if (activeRef.current && isRecordingRef.current && !aiSpeakingRef.current && !aiTypingRef.current)
      startSpeechRef.current();
  }, []);

  // ── TTS (Kokoro in the browser, else the backend, else the browser's built-in voice) ─────
  const silenceAI = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; audioRef.current = null; }
    window.speechSynthesis?.cancel();
  }, []);

  const speakText = useCallback((text: string, onEnd?: () => void) => {
    const token = ++speakTokenRef.current;
    silenceAI();

    aiSpeakingRef.current = true;  // blocks listening, replies and check-ins from now on
    detachRecognizer();

    let done = false;
    const finish = () => {
      if (done || token !== speakTokenRef.current) return;
      done = true;
      setVoicePending(false); setAiSpeaking(false); aiSpeakingRef.current = false;
      turnOpenedAtRef.current = performance.now();
      onEnd?.();
      setTimeout(resumeListening, 300);
    };
    if (!voiceEnabledRef.current) { finish(); return; }

    const started = () => {
      if (token !== speakTokenRef.current) return;
      setVoicePending(false); setAiSpeaking(true);
    };
    setVoicePending(true);

    // Sentences play in order as they arrive; the next one is generated while one plays
    const queue: Blob[] = [];
    let playing = false, ended = false, gotAny = false;
    const playNext = () => {
      if (token !== speakTokenRef.current) return;  // a newer utterance replaced this one
      const blob = queue.shift();
      if (!blob) { playing = false; if (ended) finish(); return; }
      playing = true;
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      const next = () => { URL.revokeObjectURL(url); playNext(); };
      audio.onplaying = started;
      audio.onended = next;
      audio.onerror = next;
      audio.play().catch(next);
    };
    (async () => {
      try {
        for await (const blob of conversationService.speakStream(text.slice(0, 2000))) {
          if (token !== speakTokenRef.current) return;
          gotAny = true; queue.push(blob);
          if (!playing) playNext();
        }
      } catch {
        if (token !== speakTokenRef.current) return;
        if (!gotAny) {
          // Browser fallback
          const synth = window.speechSynthesis; synth.cancel();
          const utt = new SpeechSynthesisUtterance(text);
          const v = synth.getVoices().find((v) => v.lang.startsWith("en")) ?? null;
          if (v) utt.voice = v; utt.rate = 0.9;
          utt.onstart = started; utt.onend = finish; utt.onerror = finish; synth.speak(utt);
          return;
        }
      }
      ended = true;
      if (!playing) finish();
    })();
  }, [detachRecognizer, resumeListening, silenceAI]);

  // ── Auto-reply after user speech (real OpenAI chat) ─────────────────────
  const triggerAIReply = useCallback(async (spokenText: string) => {
    if (!activeRef.current || aiTypingRef.current || aiSpeakingRef.current) return;
    if (!spokenText.trim()) return;
    const gen = ++replyGenRef.current;  // a fix to this message while the reply is written makes it stale

    const userMsg: Message = { role: "user", text: spokenText.trim(), ts: Date.now() };
    setMessages((p) => [...p, userMsg]);
    setAiTyping(true); aiTypingRef.current = true;
    if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
    pendingUserSpeechRef.current = ""; setPendingSpeech(false); replyAsapRef.current = false;
    detachRecognizer();  // the user's turn is over; nothing said now would be answered

    // Build conversation history for the API (last 12 msgs + the new user msg)
    const history = [...messagesRef.current, userMsg].slice(-12).map((m) => ({
      role: (m.role === "ai" ? "assistant" : "user") as "assistant" | "user",
      content: m.text,
    }));

    try {
      const { reply, progress, total_questions } = await conversationService.partnerReply(
        history,
        modeRef.current,
        modeRef.current === "Conversation" ? currentTopicRef.current : undefined,
        backendSessionIdRef.current ?? undefined,
      );
      if (gen !== replyGenRef.current) return;  // the user corrected what they said: that reply was for the misheard words
      if (progress && total_questions) setPlanProgress({ asked: Math.min(progress.asked, total_questions), total: total_questions });

      setAiTyping(false); aiTypingRef.current = false;
      setMessages((p) => [...p, { role: "ai", text: reply, ts: Date.now() }]);
      speakText(reply);
    } catch {
      // Fallback: preset prompts when API key is missing or network fails
      const prompts = MODE_PROMPTS[modeRef.current];
      const idx = promptIndexRef.current;
      setTimeout(() => {
        if (gen !== replyGenRef.current) return;
        setAiTyping(false); aiTypingRef.current = false;
        let reply: string;
        if (idx < prompts.length) {
          const acks = MODE_ACKS[modeRef.current];
          const ack  = acks[Math.floor(Math.random() * acks.length)] ?? "";
          reply = ack + prompts[idx];
          promptIndexRef.current = idx + 1;
        } else {
          reply = modeRef.current === "Interview"
            ? "Excellent — that wraps up our interview session. End the session to see your full assessment."
            : "Great work — you've covered everything beautifully. End the session to review your results.";
        }
        setMessages((p) => [...p, { role: "ai", text: reply, ts: Date.now() }]);
        speakText(reply);
      }, 900 + Math.random() * 500);
    }
  }, [speakText, detachRecognizer]);

  useEffect(() => { triggerAIReplyRef.current = triggerAIReply; }, [triggerAIReply]);

  // "Fix": correct a misheard message. In Conversation, if the AI is still writing its reply to
  // it, that reply is dropped and asked again with the right words. (Interview and Q&A replies
  // advance the server's question plan, so there the fix corrects the record and the feedback only.)
  const fixMessage = useCallback((i: number, text: string) => {
    const t = text.trim();
    const msgs = messagesRef.current;
    if (!t || msgs[i]?.role !== "user" || msgs[i].text === t) return;
    if (i === msgs.length - 1 && aiTypingRef.current && modeRef.current === "Conversation") {
      replyGenRef.current++;
      messagesRef.current = msgs.slice(0, -1);
      setMessages(messagesRef.current);
      setAiTyping(false); aiTypingRef.current = false;
      triggerAIReplyRef.current(t);
      return;
    }
    setMessages((p) => p.map((m, j) => (j === i ? { ...m, text: t } : m)));
  }, []);

  // ── Backchannels ──────────────────────────────────────────────────────────
  const prefetchBackchannels = useCallback(async () => {
    const urls = await Promise.all(
      BACKCHANNEL_TEXTS.map((text) =>
        conversationService.speak(text).then((b) => URL.createObjectURL(b)).catch(() => null),
      ),
    );
    backchannelUrlsRef.current = urls.filter(Boolean) as string[];
  }, []);

  const playBackchannel = useCallback(() => {
    const urls = backchannelUrlsRef.current;
    if (!urls.length || !voiceEnabledRef.current || aiSpeakingRef.current) return;
    const audio = new Audio(urls[Math.floor(Math.random() * urls.length)]);
    audio.volume = 0.5; backchannelAudioRef.current = audio;
    audio.play().catch(() => {});
  }, []);

  useEffect(() => {
    if (!speechActive || aiSpeaking || !sessionStarted) {
      if (backchannelTimerRef.current) clearInterval(backchannelTimerRef.current);
      return;
    }
    backchannelTimerRef.current = setInterval(() => {
      if (Date.now() - lastBackchannelRef.current >= 14000 + Math.random() * 8000) {
        lastBackchannelRef.current = Date.now(); playBackchannel();
      }
    }, 4000);
    return () => { if (backchannelTimerRef.current) clearInterval(backchannelTimerRef.current); };
  }, [speechActive, aiSpeaking, sessionStarted, playBackchannel]);

  // ── Speech-to-text (backend) ─────────────────────────────────────────────
  const startSpeech = useCallback(() => {
    if (voiceListenerRef.current) return;  // never two listeners at once

    // First sound after the AI's turn: how long the user took to start answering
    const noteAnswerStarted = () => {
      const opened = turnOpenedAtRef.current;
      if (opened == null) return;
      turnOpenedAtRef.current = null;
      latenciesRef.current.push(Math.round((performance.now() - opened) / 100) / 10);
    };

    // One finished utterance
    const onFinal = (text: string, replyDelayMs: number) => {
      lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
      appendTranscript(text);
      const words = text.trim().split(/\s+/).filter(Boolean);
      wordListRef.current.push(...words);
      pendingUserSpeechRef.current += (pendingUserSpeechRef.current ? " " : "") + text.trim();
      if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
      const replyWhenQuiet = () => {
        // Still talking, or their next words are being transcribed: check again shortly
        // (that transcript resets this timer with everything said)
        if (voiceListenerRef.current?.isBusy) { autoReplyTimerRef.current = setTimeout(replyWhenQuiet, 500); return; }
        const spoken = pendingUserSpeechRef.current.trim();
        pendingUserSpeechRef.current = ""; setPendingSpeech(false);
        if (spoken) triggerAIReplyRef.current(spoken);
      };
      replyWhenQuietRef.current = replyWhenQuiet;
      setPendingSpeech(true);
      autoReplyTimerRef.current = setTimeout(replyWhenQuiet, replyAsapRef.current ? 0 : replyDelayMs);
    };

    const opened = () => {
      setSpeechActive(true);
      const mr = mediaRecorderRef.current;
      if (mr?.state === "paused") { try { mr.resume(); } catch { /* unsupported */ } }
    };

    const unavailable = () => {
      sttAvailableRef.current = false; setSttAvailable(false); setInterimText("");
    };
    // Backend transcription (cloud Whisper) of each spoken turn
    if (!sttAvailableRef.current || !streamRef.current) return;
    const listener: VoiceTurnListener = new VoiceTurnListener((wav) => {
        sttAudioSecRef.current.push(Math.round(Math.max(0, wav.size - 44) / 32000 * 10) / 10);  // 16 kHz 16-bit mono WAV
        return conversationService.transcribe(wav, sttContextRef.current);
      }, {
      onSpeechStart: () => {
        noteAnswerStarted();
        // The user is (still) talking: a pending reply now waits (see replyWhenQuiet)
        lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
        setInterimText("Hearing you…");
      },
      onTranscribing: () => setInterimText("Transcribing…"),
      // A phrase (the user may still be talking) or the end of a turn (~1.6 s of silence)
      onText: (text) => {
        sttFailsRef.current = 0; setSttNotice("");
        setInterimText(listener.isSpeaking ? "Hearing you…" : "");
        if (text) { setNewestPhrase({ text: text.trim(), key: Date.now() }); onFinal(text, 1200); }
      },
      onError: (e) => {
        // One failed phrase (already retried) isn't an outage: ask again and keep listening.
        // Only no STT on the server (503) or three failures in a row switch to typing.
        sttFailsRef.current++;
        if (!(e instanceof ApiError && e.status === 503) && sttFailsRef.current < 3) {
          setInterimText(""); setSttNotice("Sorry, I didn't catch that. Please say it again.");
          return;
        }
        listener.stop();
        if (voiceListenerRef.current === listener) voiceListenerRef.current = null;
        setSpeechActive(false); unavailable();
      },
    });
    try { listener.start(streamRef.current); voiceListenerRef.current = listener; opened(); }
    catch { unavailable(); }
  }, [appendTranscript]);

  useEffect(() => { startSpeechRef.current = startSpeech; }, [startSpeech]);


  // "I'm done, reply now": answer as soon as the last words are transcribed, without the usual wait
  const replyNow = useCallback(() => {
    replyAsapRef.current = true;
    if (pendingUserSpeechRef.current.trim()) {
      if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
      replyWhenQuietRef.current();
    }
  }, []);

  const interruptAI = useCallback(() => {
    speakTokenRef.current++;  // cancels a voice still loading, and the old utterance's callbacks
    silenceAI();
    setVoicePending(false); setAiSpeaking(false); aiSpeakingRef.current = false;
    setTimeout(resumeListening, 120);
  }, [resumeListening, silenceAI]);

  // ── Camera ────────────────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    setCamError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        // Echo cancellation keeps the AI's voice out of the mic; noise suppression and
        // auto gain keep quiet or distant speech at a level recognition can use
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      if (trackVideoRef.current) trackVideoRef.current.srcObject = stream;
      const { width, height } = stream.getVideoTracks()[0]?.getSettings() ?? {};
      if (width && height) setCamAspect(`${width} / ${height}`);
      setCameraOn(true);
      startMeter(stream);

      // Record the session (audio+video together) so it can be uploaded for
      // real backend analysis once the session ends.
      try {
        recordedChunksRef.current = [];
        const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
          ? "video/webm;codecs=vp9,opus"
          : MediaRecorder.isTypeSupported("video/webm") ? "video/webm" : "";
        const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        mr.ondataavailable = (e) => { if (e.data.size > 0) recordedChunksRef.current.push(e.data); };
        mr.start(1000);
        recStartRef.current = Date.now();
        mediaRecorderRef.current = mr;
      } catch { /* MediaRecorder unsupported — session still works, just without backend analysis */ }
    } catch (e) {
      const name = e instanceof DOMException ? e.name : "";
      setCamError(
        name === "NotAllowedError" ? "Camera and microphone access was blocked. Allow it in your browser's address bar, then reload this page."
        : name === "NotFoundError" ? "No camera or microphone was found. Connect one and reload, or type your replies below."
        : name === "NotReadableError" ? "Your camera or microphone is being used by another app. Close it and reload."
        : "Couldn't start your camera and microphone. You can still type your replies below.");
    }
  }, [setCameraOn, startMeter]);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const mr = mediaRecorderRef.current;
      if (!mr || mr.state === "inactive") { resolve(null); return; }
      mr.onstop = () => {
        resolve(recordedChunksRef.current.length
          ? new Blob(recordedChunksRef.current, { type: "video/webm" })
          : null);
      };
      mr.stop();
    });
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    if (trackVideoRef.current) trackVideoRef.current.srcObject = null;
    setCameraOn(false);
    stopMeter();
  }, [setCameraOn, stopMeter]);

  // ── Session start / end ───────────────────────────────────────────────────
  const startSession = useCallback(async () => {
    // The backend session comes first: without it nothing would be recorded or analysed, so a
    // failure (signed out, no consent, server down) stops here instead of after the whole talk
    let backendSession = prepared;
    if (!backendSession) {
      setStartError(null);
      try {
        backendSession = await liveService.start({ session_type: mode, topic: mode === "Conversation" ? currentTopicRef.current : undefined });
      } catch (e) {
        setStartError(e instanceof ApiError && e.status === 403
          ? "Agree to cloud processing (the box that just opened) to start the session."
          : "Couldn't start the session. Check your connection and try again.");
        return;
      }
    }
    wordListRef.current = [];
    lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
    sttAudioSecRef.current = [];
    activeRef.current = true; startTimeRef.current = performance.now(); sessionStartedAtRef.current = Date.now();
    turnOpenedAtRef.current = null; latenciesRef.current = [];
    pendingUserSpeechRef.current = "";

    setSessionStarted(true); setRecording(true); setWpm(0);
    setDuration(0); setTranscript("");

    // A backend live session (for recording + analysis) needs sign-in. Interview and
    // Presentation Q&A sessions were prepared on their setup page (with a question plan).
    const [health] = await Promise.all([
      api.health().catch(() => null),
      startCamera(),
    ]);
    if (voiceEnabledRef.current) conversationService.preloadVoice();
    // Transcribe the user's turns on the backend when it has a speech model
    // An unreachable /health isn't proof STT is down: try voice, /stt's own 503 settles it
    const stt = health ? Boolean(health.providers?.openai) : true;
    sttFailsRef.current = 0; setSttNotice("");
    sttAvailableRef.current = stt; setSttAvailable(stt);
    backendSessionIdRef.current = backendSession.id;

    timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    startTracking();
    if (isTalkRef.current) {
      // Presenting: the user talks, the AI stays silent; the analysis afterwards uses the recording
      // and when each slide was shown (from the start of the recording)
      slideTimesRef.current = [{ slide_index: slideIdxRef.current, t_sec: 0 }];
      return;
    }
    prefetchBackchannels();
    startSpeech();

    // The opening line: the plan's intro (interview / Q&A) or a greeting from the partner;
    // scripted when no LLM is available
    setAiTyping(true); aiTypingRef.current = true;
    let firstMsg = MODE_PROMPTS[mode][0];
    try {
      const r = await conversationService.partnerReply(
        [], mode, mode === "Conversation" ? currentTopicRef.current : undefined, backendSession.id);
      firstMsg = r.reply;
      if (r.progress && r.total_questions) setPlanProgress({ asked: r.progress.asked, total: r.total_questions });
    } catch { promptIndexRef.current = 1; }
    setAiTyping(false); aiTypingRef.current = false;
    if (!activeRef.current) return;
    setMessages([{ role: "ai", text: firstMsg, ts: Date.now() }]);
    speakText(firstMsg);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, speakText, prepared]);

  // Load the prepared session (interview setup / deck Q&A); without one, go and prepare it
  useEffect(() => {
    if (mode === "Conversation") return;
    if (!liveParam) { router.replace(mode === "Interview" ? "/interview" : "/presentations"); return; }
    liveService.get(liveParam)
      .then((s) => {
        if (s.status !== "active" || s.has_recording) {
          router.replace(`/results/${s.id}`);
          return;
        }
        setPrepared(s);
        const total = s.context?.plan?.questions?.length;
        if (total) setPlanProgress({ asked: 0, total });
      })
      .catch(() => router.replace(mode === "Interview" ? "/interview" : "/presentations"));
  }, [mode, liveParam, router]);

  const endSession = useCallback(async () => {
    setIsEnding(true); activeRef.current = false;
    speakTokenRef.current++;  // a reply whose voice is still loading must not play after the end
    setVoicePending(false);
    if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
    pendingUserSpeechRef.current = "";
    silenceAI();
    if (backchannelAudioRef.current) { backchannelAudioRef.current.pause(); backchannelAudioRef.current = null; }
    if (backchannelTimerRef.current) clearInterval(backchannelTimerRef.current);
    backchannelUrlsRef.current.forEach((u) => URL.revokeObjectURL(u));
    if (timerRef.current) clearInterval(timerRef.current);
    if (silenceCheckRef.current) clearInterval(silenceCheckRef.current);
    stopTracking();
    detachRecognizer();

    const recordedBlob = await stopRecording();
    stopCamera(); setRecording(false);

    const sessionId = backendSessionIdRef.current;
    if (!sessionId) return;  // ended before it started
    try {
      const turns = messagesRef.current.map((m) => ({
        role: m.role === "ai" ? "assistant" as const : "user" as const,
        text: m.text,
        t_sec: Math.max(0, Math.round((m.ts - sessionStartedAtRef.current) / 100) / 10),
      }));
      await liveService.end(sessionId, duration, turns, {
        response_latency_sec: latenciesRef.current,
        ...(isTalkRef.current ? { slide_times: slideTimesRef.current } : {}),
        stt_audio_sec: sttAudioSecRef.current,
      });
      if (!recordedBlob) throw new Error("No recording to analyse");
      await liveService.uploadRecording(sessionId, recordedBlob);
      // The analysis runs on the server; the results page shows its progress
      await liveService.startAnalysis(sessionId);
    } catch {
      // The results page shows what's missing (no recording / not analysed) with a retry
    }
    router.push(`/results/${sessionId}`);
  }, [
    detachRecognizer, stopRecording, stopCamera, router, duration, stopTracking, silenceAI,
  ]);

  // ── Lighting & contrast check: once a second while the camera runs (independent of
  //    MediaPipe loading; uses its face box when available) ───────────────────────
  useEffect(() => {
    if (!sessionStarted || !isCameraOn) return;
    const timer = setInterval(() => {
      if (videoRef.current) setLighting(analyzeLighting(videoRef.current, faceNormRef.current));
    }, 1000);
    return () => clearInterval(timer);
  }, [sessionStarted, isCameraOn, faceNormRef]);

  // ── Silence detection ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionStarted) return;
    silenceCheckRef.current = setInterval(() => {
      if (!activeRef.current || aiTypingRef.current || aiSpeakingRef.current || isTalkRef.current) return;
      if (voiceListenerRef.current?.isBusy) { lastSpeechTimeRef.current = Date.now(); return; }
      if ((performance.now() - startTimeRef.current) / 1000 < 20) return;
      if ((Date.now() - lastSpeechTimeRef.current) / 1000 > 30 && !checkinAskedRef.current) {
        checkinAskedRef.current = true;
        const msg = CHECKIN_MESSAGES[Math.floor(Date.now() / 1000) % CHECKIN_MESSAGES.length];
        setMessages((p) => [...p, { role: "ai", text: msg, ts: Date.now() }]);
        speakText(msg);
      }
    }, 5000);
    return () => { if (silenceCheckRef.current) clearInterval(silenceCheckRef.current); };
  }, [sessionStarted, speakText]);

  // ── Toggles ───────────────────────────────────────────────────────────────
  const toggleMic = () => {
    if (!sessionStarted) return;
    streamRef.current?.getAudioTracks().forEach((t) => (t.enabled = !isRecording));
    // Presenting has no AI turns: muting only silences the mic, and the recording (which the slide
    // timings are measured against) keeps running
    if (!isTalkRef.current) { if (isRecording) detachRecognizer(); else startSpeech(); }
    setRecording(!isRecording);
  };

  // Keyboard: Space = "I'm done", Esc = interrupt the AI, M = mute/unmute (not while typing)
  const keysRef = useRef<(e: KeyboardEvent) => void>(() => {});
  useEffect(() => {
    keysRef.current = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (e.ctrlKey || e.metaKey || e.altKey || el?.closest("input, textarea, select, [contenteditable=true]")) return;
      if (isTalkRef.current) {  // presenting: the keys a clicker sends move the slides
        if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); goToSlide(slideIdxRef.current + 1); }
        else if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); goToSlide(slideIdxRef.current - 1); }
        else if (sessionStarted && e.key.toLowerCase() === "m") { e.preventDefault(); toggleMic(); }
        return;
      }
      if (!sessionStarted) return;
      if (e.key === " ") {  // always ours here: otherwise it scrolls the page or re-clicks the focused button
        e.preventDefault();
        if (pendingUserSpeechRef.current || voiceListenerRef.current?.isBusy) replyNow();
      }
      else if (e.key === "Escape" && aiSpeakingRef.current) { e.preventDefault(); interruptAI(); }
      else if (e.key.toLowerCase() === "m") { e.preventDefault(); toggleMic(); }
    };
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => keysRef.current(e);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const toggleCamera = () => {
    if (!sessionStarted) return;
    if (isCameraOn) { streamRef.current?.getVideoTracks().forEach((t) => (t.enabled = false)); setCameraOn(false); }
    else { streamRef.current?.getVideoTracks().forEach((t) => (t.enabled = true)); setCameraOn(true); }
  };

  const sendMessage = useCallback(() => {
    const text = input.trim();
    if (!text || !sessionStarted || aiTyping) return;
    if (autoReplyTimerRef.current) clearTimeout(autoReplyTimerRef.current);
    pendingUserSpeechRef.current = "";
    lastSpeechTimeRef.current = Date.now(); checkinAskedRef.current = false;
    setInput("");
    const words = text.split(/\s+/).filter(Boolean);
    wordListRef.current.push(...words);
    appendTranscript(text);
    triggerAIReplyRef.current(text);
  }, [input, sessionStarted, aiTyping, appendTranscript]);

  const shuffleTopic = useCallback(() => {
    const next = RANDOM_TOPICS[Math.floor(Math.random() * RANDOM_TOPICS.length)];
    setCurrentTopic(next);
    if (sessionStarted) {
      const reply = `Let's switch it up! Here's a new topic: ${next}`;
      setMessages((p) => [...p, { role: "ai", text: reply, ts: Date.now() }]);
      speakText(reply);
    }
  }, [sessionStarted, speakText]);

  // Closing or reloading the tab mid-session would lose the recording: ask first
  useEffect(() => {
    if (!sessionStarted || isEnding) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [sessionStarted, isEnding]);

  // ── Scroll + cleanup ──────────────────────────────────────────────────────
  // Scroll only the chat box to its latest message (scrollIntoView would also scroll the page)
  useEffect(() => {
    const box = chatEndRef.current?.closest(".overflow-y-auto");
    if (box) box.scrollTo({ top: box.scrollHeight, behavior: "smooth" });
  }, [messages, aiTyping]);
  useEffect(() => {
    return () => {
      activeRef.current = false;
      silenceAI();
      if (timerRef.current) clearInterval(timerRef.current);
      if (silenceCheckRef.current) clearInterval(silenceCheckRef.current);
      stopTracking();
      detachRecognizer(); stopCamera(); disposeTracking();
      // Leaving without clicking "End" — a MediaRecorder still attached to
      // (now-stopped) tracks won't emit further data, but stop it
      // explicitly so it isn't left in "recording" state indefinitely.
      const mr = mediaRecorderRef.current;
      if (mr && mr.state !== "inactive") { try { mr.stop(); } catch { /* already stopped */ } }
    };
  }, [stopCamera, detachRecognizer, stopTracking, disposeTracking, silenceAI]);

  // ── Derived ───────────────────────────────────────────────────────────────
  // The AI's turn before its voice starts (LLM reply + TTS loading) reads as "thinking"
  const thinking = aiTyping || voicePending;

  const mc = MODES[mode].color;
  const mcInk = inkOf(mc);  // the mode colour as readable text in either theme

  const orbState: OrbState =
    thinking   ? "thinking"  :
    aiSpeaking ? "speaking"  :
    speechActive && sessionStarted ? "listening" : "idle";

  const stateLabel =
    prepared?.context?.kind === "talk" ? (sessionStarted ? "Presenting" : "Ready to start") :
    thinking    ? "Thinking…"      :
    aiSpeaking  ? "AI speaking"    :
    speechActive && sessionStarted ? "Listening…" :
    sessionStarted ? "Your turn"   : "Ready to start";

  const currentQuestion = messages.filter((m) => m.role === "ai").at(-1)?.text ?? null;
  const setup = prepared?.context?.setup;
  const deckTitle = prepared?.context?.deck_title;
  // Presenting the deck (vs. the Q&A rehearsal)
  const isTalk = prepared?.context?.kind === "talk";
  const talkSlides = prepared?.context?.slides ?? [];
  const deckId = prepared?.context?.deck_id;
  useEffect(() => { isTalkRef.current = isTalk; slideCountRef.current = talkSlides.length; }, [isTalk, talkSlides.length]);

  // Context for speech recognition: what this session is about, then the AI's last line
  useEffect(() => {
    const lastAi = messages.filter((m) => m.role === "ai").at(-1)?.text ?? "";
    const about = mode === "Interview" && setup ? `Interview for the ${setup.position} role${setup.company ? ` at ${setup.company}` : ""}.`
      : deckTitle ? `Q&A on the presentation "${deckTitle}".` : currentTopic ? `Topic: ${currentTopic}.` : "";
    sttContextRef.current = `${about} ${lastAi}`.trim();
  }, [messages, mode, setup, deckTitle, currentTopic]);

  // ── Whose turn is it? One plain answer for the turn banner ─────────────────
  const partner = MODES[mode].partner;
  const userSpeaking = interimText === "Hearing you…";
  const transcribing = interimText === "Transcribing…";
  type Turn = { tone: "you" | "ai" | "wait" | "off"; icon: typeof Mic; title: string; hint: string };
  const turn: Turn | null =
    !sessionStarted ? null :
    aiSpeaking ? { tone: "ai", icon: Volume2, title: `${partner} is talking`, hint: "Listen. You can interrupt if you need to." } :
    thinking ? { tone: "wait", icon: Loader2, title: `${partner} is thinking…`, hint: "Your answer was received. A reply is on its way." } :
    userSpeaking ? { tone: "you", icon: Mic, title: "Listening… keep going", hint: "When you've finished, pause for about 2 seconds, or press “I'm done”." } :
    transcribing || pendingSpeech ? { tone: "you", icon: Mic, title: "Got it. Writing down what you said…", hint: "Keep talking to add more, or press “I'm done” for the reply." } :
    !sttAvailable ? { tone: "you", icon: Send, title: "Your turn: type your answer below", hint: "Voice input stopped working (speech recognition didn't respond), so please type for now." } :
    !isRecording ? { tone: "off", icon: MicOff, title: "Your microphone is muted", hint: "Unmute it (bottom-left of the video) to answer by voice, or type below." } :
    { tone: "you", icon: Mic, title: "Your turn: speak now", hint: sttNotice || "Talk naturally. Pause for about 2 seconds when you've finished." };
  const TURN_STYLE: Record<Turn["tone"], React.CSSProperties> = {
    you: { background: mc, color: "#fff" },
    ai: { background: "var(--surface-3)", color: "var(--ink)" },
    wait: { background: "var(--surface-2)", color: "var(--ink)" },
    off: { background: "var(--surface-2)", color: "var(--ink)", border: "1px dashed var(--line-strong)" },
  };
  const turnBanner = turn && (
    <div className={cn("flex-shrink-0 rounded-xl p-4 sm:p-5", turn.tone === "you" && "clay")} style={TURN_STYLE[turn.tone]}
      role="status" aria-live="polite">
      <div className="flex items-center gap-4">
        <span className={cn("w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0",
          turn.tone === "you" && userSpeaking && "animate-pulse")}
          style={{ background: turn.tone === "you" ? "rgba(255,255,255,0.22)" : "var(--surface)" }}>
          <turn.icon className={cn("w-6 h-6", turn.tone === "wait" && "animate-spin")} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-display text-xl sm:text-2xl leading-tight">{turn.title}</p>
          <p className="text-sm mt-0.5 opacity-80">{turn.hint}</p>
          {/* Live mic level while it's the user's turn: shows the mic is really hearing them */}
          {turn.tone === "you" && isRecording && sttAvailable && (
            <span className="mt-2.5 block h-1.5 w-full max-w-[240px] rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.25)" }}>
              <span className="block h-full rounded-full bg-white transition-[width] duration-100" style={{ width: `${Math.min(100, audioLevel * 260)}%` }} />
            </span>
          )}
        </div>
        {aiSpeaking && (
          <button onClick={interruptAI} className="flex-shrink-0 h-10 px-4 rounded-md text-sm font-semibold"
            style={{ background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line-strong)" }}>
            Interrupt
          </button>
        )}
        {turn.tone === "you" && (userSpeaking || transcribing || pendingSpeech) && (
          <button onClick={replyNow} className="flex-shrink-0 h-10 px-4 rounded-md text-sm font-semibold"
            style={{ background: "#fff", color: "#0A0A0A" }}>
            I&apos;m done
          </button>
        )}
      </div>
      <p className="hidden md:flex items-center gap-1.5 mt-3 text-[11px] opacity-70">
        <Keyboard className="w-3.5 h-3.5" /> Space: I&apos;m done · Esc: interrupt · M: mute
      </p>
      {planProgress && (
        <div className="mt-4 flex items-center gap-3">
          <span className="text-xs font-semibold opacity-80 whitespace-nowrap">
            Question {Math.max(1, Math.min(planProgress.asked, planProgress.total))} of {planProgress.total}
          </span>
          <span className="flex gap-1.5 flex-1">
            {Array.from({ length: planProgress.total }, (_, i) => (
              <span key={i} className="h-1.5 flex-1 rounded-full" style={{
                background: i < planProgress.asked ? (turn.tone === "you" ? "#fff" : mc) : (turn.tone === "you" ? "rgba(255,255,255,0.3)" : "var(--line)"),
              }} />
            ))}
          </span>
        </div>
      )}
    </div>
  );

  // ── Before starting: what will happen, in four steps, with the big start button ──
  const startLabel = isTalk ? "Start presenting" : mode === "Interview" ? "Start interview" : mode === "Presentation" ? "Start Q&A" : "Start conversation";
  const preparing = mode !== "Conversation" && !prepared;
  const startGuide = (
    <div className="h-full flex flex-col justify-center max-w-md mx-auto py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.12em]" style={{ color: "var(--muted)" }}>How this works</p>
      <h2 className="font-display text-3xl mt-1" style={{ color: "var(--ink)" }}>
        {isTalk ? "Present your deck" : mode === "Interview" ? `Your interview with ${partner}` : mode === "Presentation" ? "Your Q&A rehearsal" : "Just talk"}
      </h2>
      <ol className="mt-5 space-y-3.5">
        {(isTalk ? [
          [Video, "Allow your camera and microphone when the browser asks."],
          [Presentation, "Press Start, then present as you would to a real audience: to the camera, not the slide."],
          [Mic, "Move through your slides with → and ← (or the buttons). The app notes when each slide is on screen."],
          [ListChecks, "Press End when you've finished. You'll see if what you said matched each slide, plus voice and body language."],
        ] : [
          [Video, "Allow your camera and microphone when the browser asks."],
          [Volume2, `${partner} speaks first. Listen, then the big banner tells you when it's your turn.`],
          [Mic, "Answer out loud. When you've finished, pause for about 2 seconds, or press “I'm done”."],
          [ListChecks, "Press End when you're finished. Nothing is scored while you talk: your report comes after."],
        ]).map(([Icon, text], i) => {
          const I = Icon as typeof Mic;
          return (
            <li key={i} className="flex gap-3 items-start">
              <span className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-white" style={{ background: mc }}>
                <I className="w-4 h-4" />
              </span>
              <span className="text-sm leading-relaxed pt-1" style={{ color: "var(--ink-2)" }}>{text as string}</span>
            </li>
          );
        })}
      </ol>
      <button onClick={startSession} disabled={preparing}
        className="clay mt-7 h-14 rounded-lg text-base font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-60"
        style={{ background: mc }}>
        {preparing ? <><Loader2 className="w-5 h-5 animate-spin" /> {mode === "Presentation" ? "Loading your deck…" : "Getting your questions ready…"}</> : <><Mic className="w-5 h-5" /> {startLabel}</>}
      </button>
      {camError && <p className="text-sm mt-3" role="alert" style={{ color: "var(--bad)" }}>{camError}</p>}
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────

  // ── Camera stage: large clean mirror + small MediaPipe tracking inset ──────
  const stateColor =
    orbState === "listening" ? "#4ade80" : orbState === "speaking" ? "#93c5fd" :
    orbState === "thinking" ? "#fbbf24" : "rgba(255,255,255,0.55)";
  // The same state as text on a themed card (the bright stateColor is for chips over video)
  const stateInk =
    orbState === "listening" ? "var(--ok)" : orbState === "speaking" ? "var(--accent-ink)" :
    orbState === "thinking" ? "var(--warn)" : "var(--muted)";
  const chip = { background: "rgba(0,0,0,0.6)" } as const;
  const LIGHT_STATUS = {
    good: { label: "Good", color: "var(--ok)" },
    fair: { label: "Could be better", color: "var(--warn)" },
    poor: { label: "Needs fixing", color: "var(--bad)" },
  } as const;
  const lightingPanel = (
    <div className="glass-card px-4 py-3 flex-shrink-0">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider">Lighting &amp; contrast</p>
        {lighting && (
          <span className="text-[11px] font-semibold" style={{ color: LIGHT_STATUS[lighting.status].color }}>
            {lighting.faceDetected ? LIGHT_STATUS[lighting.status].label : "Looking for your face"}
          </span>
        )}
      </div>
      {!lighting ? (
        <p className="text-xs text-[var(--muted)]">Checks your lighting once your camera is on.</p>
      ) : (
        <>
          <dl className="grid grid-cols-4 gap-2 mb-2.5">
            {([
              ["Face", `${Math.round(lighting.faceLum)}`, lighting.faceLum >= 90 && lighting.faceLum <= 205],
              ["Contrast", `${Math.round(lighting.contrast)}`, !lighting.faceDetected || lighting.contrast >= 18],
              ["Backlight", lighting.backgroundLum > lighting.faceLum + 15 ? "Yes" : "No", lighting.backgroundLum <= lighting.faceLum + 15],
              ["Stand-out", `${lighting.separation.toFixed(1)}:1`, lighting.separation >= 1.3],
            ] as const).map(([k, v, ok]) => (
              <div key={k}>
                <dt className="text-[9px] uppercase tracking-wide text-[var(--muted)]">{k}</dt>
                <dd className="text-xs font-semibold" style={{ color: ok ? "var(--ink)" : "var(--warn)" }}>{v}</dd>
              </div>
            ))}
          </dl>
          <ul className="space-y-1">
            {lighting.tips.slice(0, 2).map((t) => (
              <li key={t} className="text-xs leading-relaxed text-[var(--ink-2)]">{t}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );

  // On lg the camera's height comes from the viewport alone (never from the cards, whose text
  // changes every few frames while a face is tracked: that resized the camera and flickered).
  // It stays 16:9 inside that box (container query units); the cards below take what's left
  // and scroll inside it if their text runs long. ponytail: 470px = header + strip + ~2 card rows,
  // retune if those grow.
  const CAM_FIT = "lg:h-[calc(100dvh-470px)] lg:min-h-[160px] lg:flex-shrink-0 lg:grid lg:place-items-center lg:[container-type:size] lg:[&>*]:w-[min(100cqw,calc(100cqh*16/9))]";
  const CARDS_FIT = "grid lg:grid-cols-2 gap-3 lg:flex-1 lg:min-h-0 lg:overflow-y-auto lg:content-start";
  // The live transcript and the reply box, shared by the interview and conversation layouts
  const composer = (
    <>
      {(transcript || interimText) && sessionStarted && (
        <LiveTranscript transcript={transcript} newest={newestPhrase} status={interimText} color={mc} />
      )}
      <div className="flex-shrink-0 flex gap-2">
        <VoiceBeam stream={streamRef.current} listening={speechActive && sessionStarted && !aiSpeaking && !thinking} thinking={sessionStarted && thinking} color={mc}>
          <input type="text" value={input} aria-label="Type your reply"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            disabled={!sessionStarted || thinking || aiSpeaking}
            placeholder={
              !sessionStarted ? `Start the ${mode === "Interview" ? "interview" : "session"} first…` :
              aiSpeaking ? `${partner} is speaking — listen…` :
              thinking ? `${partner} is replying…` :
              !sttAvailable ? "Speech recognition unavailable — type your reply…" :
              speechActive ? "Speaking captured — or type here…" :
              "Speak aloud, or type your reply…"
            }
            className="w-full px-4 py-3 rounded-xl text-sm text-[var(--ink)] outline-none transition-all disabled:opacity-40 placeholder:text-[var(--faint)] border border-[var(--line)] focus:border-[var(--line-strong)]"
            style={{ background: "var(--surface-2)" }}
          />
        </VoiceBeam>
        <button onClick={sendMessage} aria-label="Send"
          disabled={!sessionStarted || !input.trim() || thinking || aiSpeaking}
          className="w-11 h-11 flex items-center justify-center rounded-xl text-white transition-all disabled:opacity-30 flex-shrink-0 press-effect"
          style={{ background: mc }}>
          <Send className="w-4 h-4" />
        </button>
      </div>
    </>
  );

  const cameraStage = (
    <div className="clay relative w-full flex-shrink-0 overflow-hidden rounded-xl bg-black"
      style={{ aspectRatio: "16 / 9", border: "1px solid rgba(255,255,255,0.08)" }}>
      {/* Main view — how you look to your audience, no overlay (mirrored like a mirror) */}
      <video ref={videoRef} autoPlay muted playsInline
        className={cn("absolute inset-0 w-full h-full object-cover", !isCameraOn && "hidden")}
        style={{ transform: "scaleX(-1)" }} />
      {!isCameraOn && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-white/35">
          <VideoOff className="w-8 h-8" />
          <span className="text-xs text-center max-w-sm px-4" role={startError || camError ? "alert" : undefined}
            style={startError || camError ? { color: "#fbbf24" } : undefined}>
            {startError ?? camError ?? (sessionStarted ? "Camera is off" : "Your camera appears here when the session starts")}
          </span>
        </div>
      )}

      {sessionStarted && (
        <span className="absolute top-3 left-3 flex items-center gap-1.5 text-[11px] font-semibold text-white px-2 py-1" style={chip}>
          <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> REC {formatDuration(duration)}
        </span>
      )}
      <span className="absolute top-3 right-3 text-[11px] font-semibold px-2 py-1" style={{ ...chip, color: stateColor }}>
        {stateLabel}
      </span>
      {/* Seat check: the posture the analysis will score, flagged while it can still be fixed */}
      {sessionStarted && isCameraOn && postureTip && (
        <span role="status" className="absolute top-12 left-1/2 -translate-x-1/2 max-w-[90%] text-center text-xs font-semibold px-3 py-1.5 rounded-md"
          style={{ ...chip, color: "#fbbf24" }}>
          {POSTURE_TIPS[postureTip]}
        </span>
      )}

      {/* Mic + camera controls */}
      <div className="absolute bottom-3 left-3 flex items-center gap-2">
        <button onClick={toggleMic} disabled={!sessionStarted} aria-label={isRecording ? "Mute microphone" : "Unmute microphone"}
          className={cn("relative h-9 pl-3 pr-3.5 rounded-md flex items-center gap-2 text-xs font-semibold text-white transition-colors",
            !sessionStarted && "opacity-40 cursor-not-allowed")}
          style={{ background: isRecording ? "rgba(194,52,44,0.92)" : "rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.15)" }}>
          {isRecording ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4 text-white/60" />}
          {/* Real input level */}
          <span className="w-10 h-1 bg-white/20 overflow-hidden">
            <span className="block h-full bg-white transition-[width] duration-100" style={{ width: `${Math.min(100, audioLevel * 260)}%` }} />
          </span>
        </button>
        <button onClick={toggleCamera} disabled={!sessionStarted} aria-label={isCameraOn ? "Turn camera off" : "Turn camera on"}
          className={cn("h-9 w-9 rounded-md flex items-center justify-center text-white transition-colors", !sessionStarted && "opacity-40 cursor-not-allowed")}
          style={{ background: "rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.15)" }}>
          {isCameraOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4 text-white/60" />}
        </button>
      </div>

      {/* Tracking inset — the same camera with MediaPipe's face + pose landmarks */}
      <div className="absolute bottom-3 right-3 bg-black overflow-hidden rounded-lg"
        style={{ width: "27%", minWidth: 150, aspectRatio: camAspect, border: "1px solid rgba(255,255,255,0.3)" }}>
        <video ref={trackVideoRef} autoPlay muted playsInline
          className={cn("absolute inset-0 w-full h-full object-fill", !isCameraOn && "hidden")} />
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />
        <div className="absolute bottom-0 inset-x-0 flex items-center justify-between px-1.5 py-0.5 text-[9px] font-semibold" style={chip}>
          <span className="text-white/75">Tracking</span>
          <span className="flex gap-2">
            <span style={{ color: faceDetected ? "#5eead4" : "rgba(255,255,255,0.3)" }}>Face</span>
            <span style={{ color: poseDetected ? "#93c5fd" : "rgba(255,255,255,0.3)" }}>Pose</span>
          </span>
        </div>
      </div>
    </div>
  );

  const current = talkSlides.find((t) => t.index === slideIdx);
  const talkBody = (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_340px] lg:grid-rows-[minmax(0,1fr)] gap-4 flex-1 min-h-0">
      <div className="flex flex-col gap-3 min-w-0 min-h-0">
        {/* Desktop: the slide takes only the height left after the controls, cue and thumbnails */}
        <div className="clay relative rounded-xl overflow-hidden bg-black aspect-video lg:aspect-auto lg:flex-1 lg:min-h-0">
          {deckId && (
            <SlideImage deckId={deckId} n={slideIdx} alt={`Slide ${slideIdx}${current?.title ? `: ${current.title}` : ""}`}
              className="absolute inset-0 w-full h-full object-contain" />
          )}
          {!sessionStarted && (
            <div className="absolute inset-0 flex items-end justify-center p-6" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.75), transparent 60%)" }}>
              <button onClick={startSession} disabled={preparing}
                className="clay h-14 px-8 rounded-lg text-base font-semibold text-white flex items-center gap-2 disabled:opacity-60" style={{ background: mc }}>
                {preparing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Presentation className="w-5 h-5" />} {startLabel}
              </button>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => goToSlide(slideIdx - 1)} disabled={slideIdx <= 1} aria-label="Previous slide"
            className="nav-pill h-11 px-4 rounded-full text-sm font-semibold disabled:opacity-40">← Back</button>
          <p className="flex-1 text-center text-sm tabular-nums" style={{ color: "var(--ink-2)" }} aria-live="polite">
            Slide <b style={{ color: "var(--ink)" }}>{slideIdx}</b> of {talkSlides.length}
            {current?.title ? <span className="hidden sm:inline" style={{ color: "var(--muted)" }}> · {current.title}</span> : null}
          </p>
          <button onClick={() => goToSlide(slideIdx + 1)} disabled={slideIdx >= talkSlides.length} aria-label="Next slide"
            className="h-11 px-5 rounded-full text-sm font-semibold text-white disabled:opacity-40" style={{ background: mc }}>Next →</button>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setShowCue((v) => !v)} aria-pressed={showCue} className="nav-pill px-3 py-1.5 rounded-full text-xs font-semibold">
            {showCue ? "Hide my " : "Show my "}{current?.script ? "script" : "cue"}
          </button>
          {showCue && current?.script ? (
            <p className="text-sm whitespace-pre-line max-h-40 overflow-y-auto" style={{ color: "var(--ink-2)" }}>
              {current.budget_sec ? <span style={{ color: "var(--muted)" }}>About {formatDuration(current.budget_sec)}: </span> : null}{current.script}
            </p>
          ) : showCue && current?.key_point && (
            <p className="text-sm" style={{ color: "var(--ink-2)" }}><span style={{ color: "var(--muted)" }}>This slide&apos;s point:</span> {current.key_point}</p>
          )}
        </div>
        {/* Thumbnails: jump to any slide */}
        <div className="flex gap-2 overflow-x-auto pb-1" role="list" aria-label="Slides">
          {talkSlides.map((t) => (
            <button key={t.index} role="listitem" onClick={() => goToSlide(t.index)} aria-current={t.index === slideIdx}
              aria-label={`Go to slide ${t.index}${t.title ? `: ${t.title}` : ""}`}
              className="flex-shrink-0 w-28 rounded-md overflow-hidden" style={{ outline: t.index === slideIdx ? `3px solid ${mc}` : "1px solid var(--line)", outlineOffset: t.index === slideIdx ? 1 : 0 }}>
              {deckId && (
                <SlideImage deckId={deckId} n={t.index} alt="" className="w-full aspect-video object-contain" style={{ background: "var(--surface-2)" }} />
              )}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-3 min-h-0 lg:overflow-y-auto">
        {cameraStage}
        {!sessionStarted ? <div className="glass-card p-4">{startGuide}</div> : lightingPanel}
        {sessionStarted && (
          <p className="text-xs leading-relaxed px-1" style={{ color: "var(--muted)" }}>
            Talk to the camera, not the slide. → / ← or Page Down / Up change slides (a presentation clicker works too). M mutes.
          </p>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col px-3 sm:px-6 py-4 min-h-[calc(100dvh-80px)] lg:h-[calc(100dvh-80px)] lg:min-h-0" style={{ background: "var(--bg)", color: "var(--ink)" }}>

      {/* ── Analyzing overlay ──────────────────────────────────────────── */}
      {isEnding && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)" }}
        >
          <div
            className="flex flex-col items-center gap-4 p-8 rounded-2xl text-center"
            style={{ background: "var(--surface)", border: "1px solid var(--line)", boxShadow: "var(--shadow-modal)" }}
          >
            <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-ink)]" />
            <div>
              <p className="text-sm font-bold" style={{ color: "var(--ink)" }}>Saving your session…</p>
              <p className="text-xs mt-1" style={{ color: "var(--ink-2)" }}>
                Uploading your recording. Your results page opens next and fills in as the analysis finishes.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Header: what this is, how long it's been, and the way out ──────── */}
      <div className="flex items-center justify-between pb-4 flex-shrink-0 flex-wrap gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <span className="clay text-sm font-semibold px-4 py-1.5 rounded-full text-white" style={{ background: mc }}>
            {isTalk ? "Presentation" : MODES[mode].title}
          </span>
          {sessionStarted && (
            <span className="flex items-center gap-2 font-mono text-sm font-semibold text-[var(--ink)]" aria-label="Time elapsed">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              {formatDuration(duration)}
              <HeaderPulse level={audioLevel} active={isRecording} color={mc} />
            </span>
          )}
          {sessionStarted && mpStatus === "loading" && (
            <span className="hidden sm:flex items-center gap-1.5 text-xs text-[var(--muted)]">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Starting body-language tracking…
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {!isTalk && <button onClick={() => setVoiceEnabled((v) => !v)} aria-pressed={voiceEnabled}
            title={voiceEnabled ? "The AI's replies are spoken aloud" : "The AI's replies are shown as text only"}
            className="flex items-center gap-1.5 text-sm font-medium h-10 px-4 rounded-full transition-colors"
            style={{ background: "var(--surface-3)", color: voiceEnabled ? "var(--ink)" : "var(--muted)" }}>
            {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            {voiceEnabled ? "Voice on" : "Voice off"}
          </button>}
          {!sessionStarted ? (
            <button onClick={startSession} disabled={preparing}
              className="flex items-center gap-2 h-10 px-5 rounded-md text-sm font-semibold text-white disabled:opacity-60"
              style={{ background: "var(--accent)" }}>
              {preparing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
              {startLabel}
            </button>
          ) : (
            <button onClick={endSession} disabled={isEnding}
              className="flex items-center gap-2 h-10 px-5 rounded-md text-sm font-semibold text-white disabled:opacity-50"
              style={{ background: "var(--color-error)" }}>
              {isEnding ? <Loader2 className="w-4 h-4 animate-spin" /> : <PhoneOff className="w-4 h-4" />}
              End &amp; get feedback
            </button>
          )}
        </div>
      </div>

      {drillFocus && (
        <div className="clay mb-4 flex-shrink-0 rounded-xl px-4 py-3 flex items-center gap-3" style={{ background: "var(--peach)", color: "#0A0A0A" }}>
          <span className="text-xs font-semibold uppercase tracking-[0.12em] opacity-70 whitespace-nowrap">Today&apos;s drill</span>
          <span className="text-sm font-medium">{drillFocus}</span>
        </div>
      )}

      {/* ── Body ── */}
      {isTalk ? talkBody : mode === "Interview" ? (

        /* ── Interview Room ─────────────────────────────────────────────── */
        <div className="flex flex-col lg:flex-row flex-1 gap-4 min-h-0">

          {/* LEFT: Interviewer panel */}
          <div className="flex flex-col gap-3 w-full lg:w-[60%] lg:flex-shrink-0 lg:min-h-0">

            <div className={CAM_FIT}>{cameraStage}</div>
            <div className={CARDS_FIT}>
            {lightingPanel}

            {/* Current question card */}
            {currentQuestion && (
              <div className="glass-card rounded-2xl p-4 flex-shrink-0">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-[var(--lavender)]" />
                  <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider">Current Question</p>
                </div>
                <p className="text-sm text-[var(--ink)] leading-relaxed"
                  style={{ display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" } as React.CSSProperties}>
                  {currentQuestion}
                </p>
              </div>
            )}
            </div>
          </div>

          {/* RIGHT: whose turn + interviewer + responses */}
          <div className="flex-1 flex flex-col gap-3 min-w-0 min-h-0">
            {turnBanner}

            {/* Interviewer tile */}
            {/* A teal Clay card in both themes: the avatar is drawn for a dark room */}
            <div className="clay relative overflow-hidden flex-shrink-0 rounded-xl" style={{ height: 210, background: "var(--teal)" }}>
              <div className="absolute top-0 inset-x-0 px-4 py-2.5 flex items-center justify-between z-10"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                <div className="flex items-center gap-2">
                  <Briefcase className="w-3.5 h-3.5 text-white/60" />
                  <p className="text-white text-xs font-semibold">{partner} · Interviewer</p>
                </div>
                {aiSpeaking && (
                  <span className="flex items-center gap-1 text-[10px] font-semibold text-[#A4D4C5]">
                    <Volume2 className="w-3 h-3" /> Speaking
                  </span>
                )}
              </div>
              <div className="w-full h-full flex items-center justify-center pt-8">
                <div className="flex flex-col items-center gap-2">
                  <PartnerBot mode={mode} state={orbState} started={sessionStarted} size={110} theme="dark" />
                  <span className="text-[11px] font-semibold text-white/70">{stateLabel}</span>
                </div>
              </div>
            </div>

            {/* What this interview is about (from the setup) */}
            <div className="glass-card p-4 flex-shrink-0">
              <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider mb-2">Your interview</p>
              {setup ? (
                <>
                  <p className="text-sm font-semibold text-[var(--ink)]">
                    {setup.position}{setup.company ? ` · ${setup.company}` : ""}
                  </p>
                  <p className="text-xs text-[var(--muted)] mt-0.5 capitalize">
                    {setup.level} level · {setup.interview_type} questions
                    {prepared?.context?.resume_text ? " · using your resume" : ""}
                  </p>
                </>
              ) : (
                <p className="text-xs text-[var(--muted)]">Loading your interview setup…</p>
              )}
              <p className="text-[11px] text-[var(--muted)] mt-3 leading-relaxed">
                Answer as you would in the real interview. {partner} asks one question at a time and may ask a
                follow-up if an answer is short. Feedback on every answer comes after you end.
              </p>
            </div>

            {/* Response transcript */}
            <div className="flex-1 glass-card rounded-2xl p-4 overflow-y-auto min-h-0">
              <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider mb-3">Your Responses</p>
              {!sessionStarted ? startGuide : messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center px-4 gap-3">
                  <Loader2 className="w-6 h-6 animate-spin" style={{ color: mcInk }} />
                  <p className="text-sm" style={{ color: "var(--muted)" }}>{partner} is getting the first question ready…</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {messages.map((msg, i) => (
                    <div key={i} className={cn("flex gap-2", msg.role === "user" && "flex-row-reverse")}
                      style={{ animation: "slide-up 0.3s cubic-bezier(0.16,1,0.3,1) forwards" }}>
                      {msg.role === "ai" && (
                        <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-[9px] font-bold text-white"
                          style={{ background: "#6B4FC4", minWidth: 24 }}>A</div>
                      )}
                      {msg.role === "ai" ? (
                        <div className="max-w-[85%] px-3 py-2 text-xs leading-relaxed"
                          style={{ background: "var(--surface-2)", color: "var(--ink)", border: "1px solid var(--line)", borderRadius: "12px 12px 12px 3px" }}>
                          {msg.text}
                        </div>
                      ) : (
                        <UserBubble text={msg.text} onFix={(t) => fixMessage(i, t)} className="px-3 py-2 text-xs leading-relaxed"
                          style={{ background: "rgba(26,58,58,0.85)", color: "white", borderRadius: "12px 12px 3px 12px" }} />
                      )}
                    </div>
                  ))}

                  {thinking && (
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                        style={{ background: "#6B4FC4", minWidth: 24 }}>A</div>
                      <div className="px-3 py-2.5 flex items-center gap-1"
                        style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: "12px 12px 12px 3px" }}>
                        {[0, 1, 2].map((i) => (
                          <span key={i} className="w-1.5 h-1.5 rounded-full bg-[var(--faint)] animate-bounce"
                            style={{ animationDelay: `${i * 0.15}s` }} />
                        ))}
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>
              )}
            </div>

            {composer}
          </div>
        </div>

      ) : (

        /* ── Default 2-column layout (Conversation / Presentation Q&A) ── */
        <div className="flex flex-col lg:flex-row flex-1 gap-4 min-h-0">

          {/* LEFT: camera stage + AI status */}
          <div className="w-full lg:w-[58%] lg:flex-shrink-0 flex flex-col gap-3 lg:min-h-0">

          <div className={CAM_FIT}>{cameraStage}</div>

          <div className={CARDS_FIT}>

          {/* AI partner status */}
          {/* The partner as a living 3D orb: it pulses while the AI talks or thinks and
              ripples with your voice while you speak */}
          <div className="glass-card px-4 py-3 flex items-center gap-4 flex-shrink-0">
            <PartnerBot mode={mode} state={orbState} started={sessionStarted} size={56} />
            <div className="min-w-0">
              <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider">{partner}</p>
              <p className="text-base font-semibold" style={{ color: stateInk }}>{stateLabel}</p>
            </div>
          </div>

          {lightingPanel}

          {/* Mood — read from the same face tracking already running above */}
          {sessionStarted && (
            <div className="glass-card rounded-2xl p-3 flex-shrink-0">
              <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider mb-2">Presence &amp; Mood</p>
              <div className="flex flex-wrap gap-1.5">
                {(Object.keys(MOOD_STATES) as MoodLabel[]).map((label) => {
                  const active = mood?.label === label;
                  const c = MOOD_STATES[label].color;
                  return (
                    <span key={label}
                      className="flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded-full transition-all duration-300"
                      style={active
                        ? { background: c, color: "#fff" }
                        : { background: "var(--surface-2)", color: "var(--muted)", border: "1px solid var(--line)" }}>
                      {active && <span className="w-1 h-1 rounded-full bg-white" />}
                      {label}{active ? ` · ${mood!.score}%` : ""}
                    </span>
                  );
                })}
              </div>
              {/* always laid out, only hidden, so the card keeps its height as detection flickers */}
              <p className={cn("text-[10px] text-[var(--faint)] mt-2", faceDetected && "invisible")}>Face not detected — centre yourself in frame.</p>
            </div>
          )}

          {/* Topic shuffler — Conversation mode */}
          {mode === "Conversation" && (
            <div className="glass-card rounded-2xl p-3 flex-shrink-0">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider">Current Topic</p>
                <button onClick={shuffleTopic}
                  className="flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-lg transition-all press-effect"
                  style={{ color: mcInk, background: `${mc}15`, border: `1px solid ${mc}25` }}>
                  <Shuffle className="w-3 h-3" /> Shuffle
                </button>
              </div>
              <p className="text-xs text-[var(--ink)] leading-relaxed line-clamp-3">{currentTopic}</p>
            </div>
          )}

          {/* Deck being rehearsed (Presentation Q&A) */}
          {mode === "Presentation" && (
            <div className="glass-card p-3 flex-shrink-0">
              <p className="text-[10px] text-[var(--muted)] font-semibold uppercase tracking-wider mb-1">Q&amp;A on your deck</p>
              <p className="text-sm font-semibold text-[var(--ink)] flex items-center gap-2">
                <Presentation className="w-4 h-4 flex-shrink-0" style={{ color: mcInk }} />
                <span className="truncate">{deckTitle ?? "Loading…"}</span>
              </p>
              <p className="text-[11px] text-[var(--muted)] mt-1.5 leading-relaxed">
                The questions come from your deck&apos;s content. Answer directly first, then give your reason or evidence.
              </p>
            </div>
          )}
          </div>
        </div>

        {/* RIGHT: whose turn + the conversation */}
        <div className="flex-1 flex flex-col gap-3 min-w-0 min-h-0">
          {turnBanner}

          {/* ── CONVERSATION / INTERVIEW / PRESENTATION: chat ──────────── */}
          <>
              {/* Chat messages */}
              <div className="flex-1 glass-card rounded-2xl p-5 overflow-y-auto min-h-0">
                {!sessionStarted ? startGuide : messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center px-8 gap-3">
                    <Loader2 className="w-6 h-6 animate-spin" style={{ color: mcInk }} />
                    <p className="text-sm" style={{ color: "var(--muted)" }}>{partner} is getting ready…</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((msg, i) => (
                      <div key={i} className={cn("flex gap-3", msg.role === "user" && "flex-row-reverse")}
                        style={{ animation: "slide-up 0.3s cubic-bezier(0.16,1,0.3,1) forwards" }}>
                        {msg.role === "ai" && (
                          <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ background: mc }}>
                            <Activity className="w-3.5 h-3.5 text-white" />
                          </div>
                        )}
                        {msg.role === "ai" ? (
                          <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-tl-sm text-sm leading-relaxed"
                            style={{ background: "var(--surface-2)", color: "var(--ink)", border: "1px solid var(--line)" }}>
                            {msg.text}
                          </div>
                        ) : (
                          <UserBubble text={msg.text} onFix={(t) => fixMessage(i, t)} className="px-4 py-3 rounded-2xl rounded-tr-sm text-sm leading-relaxed"
                            style={{ background: `${mc}d0`, color: "white" }} />
                        )}
                      </div>
                    ))}

                    {/* AI thinking */}
                    {thinking && (
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ background: mc }}>
                          <Activity className="w-3.5 h-3.5 text-white" />
                        </div>
                        <div className="px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1.5"
                          style={{ background: "var(--surface-2)", border: "1px solid var(--line)" }}>
                          {[0,1,2].map((i) => (
                            <span key={i} className="w-1.5 h-1.5 rounded-full bg-[var(--faint)] animate-bounce"
                              style={{ animationDelay: `${i * 0.15}s` }} />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI speaking indicator in chat */}
                    {aiSpeaking && !thinking && (
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                          style={{ background: mc }}>
                          <Volume2 className="w-3.5 h-3.5 text-white animate-pulse" />
                        </div>
                        <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl rounded-tl-sm"
                          style={{ background: `${mc}15`, border: `1px solid ${mc}25` }}>
                          <span className="text-xs font-medium" style={{ color: mcInk }}>Speaking…</span>
                          <div className="flex items-end gap-[2px]">
                            {[3,5,8,5,3,6,8].map((h,i) => (
                              <span key={i} className="rounded-full" style={{
                                display: "block", width: 2, height: h,
                                background: mc, animation: `waveform-bar 0.6s ease-in-out ${i*80}ms infinite`,
                              }} />
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>
                )}
              </div>

              {composer}
          </>
        </div>
        </div>
      )}

      {/* ── Bottom strip: what happens next (no live scores: feedback comes after) ── */}
      <div className="flex-shrink-0 mt-3 glass-card px-4 py-2.5 flex flex-wrap items-center gap-x-6 gap-y-1 text-[11px] text-[var(--muted)]">
        <span className="flex items-center gap-1.5"><ListChecks className="w-3.5 h-3.5" />
          Analysed after you end: voice, language, body language, confidence{mode === "Conversation" ? "" : " and the content of every answer"}
        </span>
        {sessionStarted && <VolumeMeter level={audioLevel} muted={!isRecording} />}
        {wpm > 0 && <span>Pace so far: <b className="text-[var(--ink)]">{wpm} wpm</b> (120–160 is comfortable)</span>}
      </div>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-[calc(100vh-60px)]">
        <div className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: "#3E6FB0", borderTopColor: "transparent" }} />
      </div>
    }>
      <SessionContent />
    </Suspense>
  );
}
