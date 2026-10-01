export interface User {
  id: string;
  full_name: string;
  email: string;
  role: string;
  language: string;
  age_group: string | null;
  communication_goal: string | null;
  skill_level: string;
  challenges: string[];
  created_at: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  language?: string;
  age_group?: string;
  communication_goal?: string;
  skill_level?: string;
  challenges?: string[];
}

export interface UserProfile {
  id: string;
  user_id: string;
  age_group: string;
  communication_goal: string;
  skill_level: "Beginner" | "Intermediate" | "Advanced";
  challenges: string[];
}

export type SessionType = "Conversation" | "Interview" | "Presentation" | "Pronunciation";

// A live practice session (camera + mic with the AI partner) — GET /api/live/{id}
export interface LiveSession {
  id: string;
  session_type: SessionType;
  duration_sec: number;
  status: "active" | "analyzing" | "complete" | "failed";
  has_recording: boolean;
  error_detail: string | null;
  warnings: string[];
  analysis: FullAnalysisResult | null;
  created_at: string;
}

// Scores are null when the model that measures them wasn't available
// (see FullAnalysisResult.warnings) — the backend never invents a number.
export interface SpeechAnalysis {
  id: string;
  session_id: string;
  fluency_score: number | null;
  pronunciation_score: number | null;
  speaking_rate: number | null;
  filler_word_count: number | null;
  stuttering_score: number | null;
}

export interface VisionAnalysis {
  id: string;
  session_id: string;
  eye_contact_score: number | null;
  confidence_score: number | null;
  posture_score: number | null;
  emotion_label: string | null;
}

export interface AIFeedback {
  id: string;
  session_id: string;
  summary: string;
  recommendations: string[];
  created_at: string;
}

export interface ProgressRecord {
  id: string;
  live_session_id: string;
  metric_name: string;
  metric_value: number;
  recorded_at: string;
}

export interface Report {
  id: string;
  report_type: string;
  report_url: string;
  content: Record<string, unknown>;
  created_at: string;
}

export interface LiveFeedback {
  fluency: number;
  pronunciation: number;
  eye_contact: number;
  confidence: number;
  speaking_pace: number;
  posture: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Result of the live-session analysis (GET /api/live/{id} → analysis).
// Any score is null when the model that measures it isn't installed or the
// signal was missing (no transcript, no face in frame) — `warnings` says which.
export interface FullAnalysisResult {
  session_id: string;
  transcript: string | null;
  duration_sec: number;
  warnings?: string[];
  language: {
    primary_language: string;
    is_code_switching: boolean;
    accent_type: string;
    english_ratio: number;
    malay_ratio: number;
    manglish_particles: string[];
    detected_bm_words: string[];
    // Pronunciation deviations sorted into consistent Malaysian-English
    // phonology (regional, not an error) vs. ones that cost intelligibility.
    // Not produced by the backend yet — the assessment page shows samples.
    pronunciation_flags?: {
      word: string;
      category: "regional" | "intelligibility";
      note: string;
    }[];
  } | null;
  speech: {
    fluency_score: number | null;
    speaking_rate: number | null;
    pronunciation_score: number | null;
    stuttering_score: number | null;
    stuttering_severity: string | null;
    filler_count: number | null;
    filler_per_minute: number | null;
    top_filler: string | null;
    pause_frequency: number | null;
    fluency_grade: string | null;
  };
  vision: {
    eye_contact_score: number | null;
    posture_score: number | null;
    dominant_emotion: string | null;
    confidence_score: number | null;
    confidence_label: string | null;
  };
  communication_score: {
    overall_score: number | null;
    grade: string | null;
    strengths: string[];
    improvement_areas: string[];
    scored_on: string[];
  };
  recommendations: {
    summary?: string;
    source?: "llm" | "rules";
    weekly_focus: string;
    daily_target_minutes: number;
    next_session_type: string;
    tips: string[];
    progress_forecast: string;
    exercises: {
      title: string;
      description: string;
      practice_type: string;
      daily_minutes: number;
      priority: string;
      metric_target: string;
      // Measured basis for the recommendation (numbers / moments), why it matters
      area?: string;
      evidence?: string;
      why?: string;
    }[];
  };
  // Full per-model output (fluency, fillers, stuttering events, pronunciation
  // word scores, eye contact, posture, emotion, confidence breakdown)
  details: Record<string, unknown>;
}

// Gaze Tunneling — fuses two signals that every competitor (Elqo included)
// reports as separate dashboard cards: where you were looking, and when
// your speech broke down. Computed entirely client-side from the same
// face-tracking + speech-recognition already running during a live
// session (see computeGazeTunneling in the session page), not a backend
// call — the correlation is real arithmetic over real per-window samples,
// not a canned demo number.
export interface GazeTunnelingWindow {
  t: number;              // window start, seconds into the session
  eyeContact: number;     // average eye-contact score in this window, 0–100
  disfluencyCount: number;// filler words + repeated-word events in this window
}

export interface GazeTunnelingResult {
  windows: GazeTunnelingWindow[];
  windowSeconds: number;
  correlation: number;      // Pearson r between gaze aversion and disfluency density, -1..1
  coOccurrencePct: number;  // % of disfluency events that landed within one window of a gaze dip
  totalEvents: number;
  label: "Strong link" | "Some link" | "No clear link" | "Not enough data";
}

// ── Presentation coaching (PresentCoach) ──────────────────────────────────
// Mirrors the Pydantic schemas in backend/app/schemas.

export type DeckStatus =
  | "queued"
  | "processing_slides"
  | "analyzing_content"
  | "generating_scripts"
  | "synthesizing_audio"
  | "assembling_video"
  | "complete"
  | "failed";

export interface DeckListItem {
  session_id: string;
  original_filename: string;
  status: DeckStatus;
  slide_count: number | null;
  created_at: string;
}

export interface DeckStatusResponse {
  session_id: string;
  status: DeckStatus;
  slide_count: number | null;
  slides_progress: { rendered: number; scripted: number; synthesized: number; total: number } | null;
  error_detail: string | null;
  warnings: string[];
  video_ready: boolean;
  voice_cloning_used: boolean | null;
  narrator_voice: string | null;
  insights: DeckInsights | null;
  original_filename: string;
  created_at: string;
  updated_at: string;
}

// Understanding of the deck, computed before narration (backend deck_insights.py)
export interface DeckInsights {
  summary: string;
  main_message: string;
  audience: string;
  structure: { section: string; slides: number[] }[];
  slides: { slide_index: number; key_point: string }[];
  strengths: string[];
  suggestions: { slide_index: number | null; issue: string; suggestion: string }[];
  likely_questions: string[];
  source: "llm" | "rules";
  stats: {
    slide_count: number;
    total_words: number;
    estimated_minutes: [number, number];
    text_heavy_slides: number[];
    no_text_slides: number[];
  };
}

export interface SlideScript {
  slide_index: number;
  script_text: string | null;
  word_count: number | null;
  script_source: "vlm" | "fallback" | null;
  audio_source: "elevenlabs_clone" | "malaysian_tts" | "kokoro" | "openai_tts" | "espeak" | "silence" | null;
  start_sec: number | null;
  duration_sec: number | null;
  status: string;
}

export type PracticeStatus = "queued" | "transcribing" | "analyzing" | "complete" | "failed";
export type RecordingGranularity = "whole_deck" | "per_slide";

export interface PracticeMetrics {
  duration_sec: number;
  ideal_duration_sec: number | null;
  duration_ratio: number | null;
  pause_count: number;
  total_pause_sec: number;
  longest_pause_sec: number;
  long_pauses: { at_sec: number; duration_sec: number }[];
  ideal_wpm: number | null;
  has_transcript: boolean;
  // Only present when a transcript was produced
  word_count?: number;
  wpm?: number | null;
  filler_word_count?: number;
  filler_words?: Record<string, number>;
  fillers_per_minute?: number | null;
  script_coverage?: number | null;
  missed_key_terms?: string[];
}

export interface OISObservation {
  slide_index: number | null;
  observation: string;
  impact: string;
  suggestion: string;
}

export interface CoachFeedback {
  encouragement: string;
  observations: OISObservation[];
  source: "llm" | "rule_based" | string;
}

export interface AudienceFeedback {
  audience_profile: string;
  overall_impression?: string;
  clarity_score: number;
  engagement_score: number;
  engaging_moments?: string[];
  confusing_moments: string[];
  key_takeaway: string;
  questions_i_would_ask: string[];
  source?: string;
}

export interface PracticeRun {
  practice_id: string;
  session_id: string;
  status: PracticeStatus;
  recording_granularity: RecordingGranularity;
  slide_index: number | null;
  error_detail: string | null;
  warnings: string[];
  transcript: string | null;
  metrics: PracticeMetrics | null;
  feedback: CoachFeedback | null;
  audience_feedback: AudienceFeedback | null;
  created_at: string;
}

export interface CoachChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
}

export interface NarratorVoices {
  available: boolean;   // is the local Malaysian TTS installed?
  default: string;
  voices: { id: string; label: string }[];
}

export interface BackendHealth {
  status: string;
  binaries: Record<string, boolean>;
  local_ml: Record<string, boolean>;
  // Where chat / feedback / slide scripts go: "custom" = LLM_BASE_URL (e.g. local Ollama)
  llm: { provider: "openai" | "custom" | null; base_url: string | null; model: string | null; vision_model: string | null };
  tts: { base_url: string | null; voice: string | null };
  providers: { openai: boolean; elevenlabs: boolean };
}
