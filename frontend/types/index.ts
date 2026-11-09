export interface User {
  id: string;
  full_name: string;
  email: string;
  role: string;
  age_group: string | null;
  communication_goal: string | null;
  skill_level: string;
  challenges: string[];
  // Who the AI is talking to: it pitches questions, vocabulary and feedback at these
  study_level: StudyLevel | null;
  field_of_study: string | null;
  feedback_style: FeedbackStyle | null;
  cloud_consent_at: string | null;   // when they agreed to cloud processing (Groq, Gemini); null = not yet
  keep_recordings: boolean;          // keep raw recordings after analysis (default: deleted)
  created_at: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  age_group?: string;
  communication_goal?: string;
  skill_level?: string;
  challenges?: string[];
  study_level?: StudyLevel;
  field_of_study?: string;
  feedback_style?: FeedbackStyle;
  keep_recordings?: boolean;
}

export type StudyLevel = "Secondary" | "Pre-university" | "Undergraduate" | "Postgraduate" | "Working professional";
export type FeedbackStyle = "encouraging" | "balanced" | "direct";

export interface UserProfile {
  id: string;
  user_id: string;
  age_group: string;
  communication_goal: string;
  skill_level: "Beginner" | "Intermediate" | "Advanced";
  challenges: string[];
}

// The three practice functions. "Presentation" = Q&A rehearsal on an uploaded deck.
export type SessionType = "Conversation" | "Interview" | "Presentation";

export interface InterviewSetup {
  position: string;
  company?: string;
  level: "internship" | "graduate" | "junior" | "mid" | "senior";
  interview_type: "behavioural" | "technical" | "mixed";
  background?: string;
  job_description?: string;
  resume_text?: string;
}

export interface PlanQuestion {
  question: string;
  assesses: string;
  look_for: string[];
  slide_index?: number | null;
}

export interface PracticePlan {
  intro: string;
  questions: PlanQuestion[];
  source: "llm" | "rules";
}

// What a prepared session carries: the interview setup or the deck, and the question plan
export interface LiveContext {
  setup?: Omit<InterviewSetup, "resume_text">;
  resume_text?: string | null;
  deck_id?: string;
  deck_title?: string;
  deck_summary?: string;
  topic?: string;
  plan?: PracticePlan;
  progress?: { asked: number; followups: number };
  // Presentation: "talk" = the user presents the deck; "qa" = audience Q&A rehearsal
  kind?: "talk" | "qa";
  slides?: TalkSlide[];
  script?: boolean;   // talk: practising the deck's written script
}

/** One slide of a deck being presented: what the talk is checked against. */
export interface TalkSlide { index: number; title: string; text: string; key_point: string; script?: string; budget_sec?: number }

/** How the talk matched one slide (analysis.content_feedback.kind === "slides"). */
export interface SlideFeedback {
  slide_index: number; title: string; key_point: string;
  seconds: number; said: string;
  coverage: number | null; missed_terms: string[];
  status: "covered" | "partly" | "missed" | "silent" | "skipped";
  alignment: number | null; covered: string; missing: string; tip: string;
  script_coverage?: number; budget_sec?: number | null;   // practising a script
}

export interface Turn {
  role: "user" | "assistant";
  text: string;
  t_sec?: number | null;
}

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
  context: LiveContext | null;
  turns: Turn[] | null;
  created_at: string;
}

export type MetricStatus = "good" | "ok" | "work" | null;

export interface PillarMetric {
  key: string;
  label: string;
  value: number;
  display: string;
  score: number | null;
  status: MetricStatus;
  range: string;
  hint: string;
}

export interface Pillar {
  key: "voice" | "language" | "body" | "confidence";
  label: string;
  score: number | null;
  status: MetricStatus;
  about: string;
  metrics: PillarMetric[];
}

export interface AnswerFeedback {
  question: string;
  relevance: number;
  structure: number;
  specificity: number;
  went_well: string;
  improve: string;
  stronger_answer: string;
  answer?: string;          // what the learner actually said (sessions analysed after Oct 2026)
}

export type ContentFeedback =
  | { kind: "answers"; source: string; summary: string; answers: AnswerFeedback[] }
  | { kind: "conversation"; source: string; summary: string; tips: string[];
      corrections: { said: string; better: string; why: string }[] }
  | { kind: "slides"; source: string; summary: string; slides: SlideFeedback[]; total_sec: number;
      script?: { coverage: number; planned_sec: number } };

export interface AuthTokens {
  access_token: string;
  refresh_token?: string | null;  // now an httpOnly cookie; absent from new responses
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
  // The simple view: four pillars of measured metrics (older sessions may not have them)
  pillars?: Record<"voice" | "language" | "body" | "confidence", Pillar>;
  // What was said, judged against the plan (interview / Q&A) or as language (conversation)
  content_feedback?: ContentFeedback | null;
  // Full per-model output (fluency, fillers, stuttering events, pronunciation
  // word scores, eye contact, posture, emotion, confidence breakdown)
  details: Record<string, unknown>;
}

// Gaze Tunneling is computed on the server: analysis.details.gaze_tunneling = {r, p, label, windows, events}.

// ── Presentation coaching (PresentCoach) ──────────────────────────────────
// Mirrors the Pydantic schemas in backend/app/schemas.

export type DeckStatus = "queued" | "processing_slides" | "analyzing_content" | "complete" | "failed";

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
  slides_rendered: number;
  error_detail: string | null;
  warnings: string[];
  insights: DeckInsights | null;
  script: DeckScript | null;
  original_filename: string;
  created_at: string;
  updated_at: string;
}

// A practice script for a deck, sized to a talk length (backend script_writer.py)
export type ScriptStyle = "full" | "points";
export interface DeckScript {
  minutes: number; style: ScriptStyle; wpm: number; source: "llm" | "rules"; created_at: string;
  unverified_terms: string[];
  read_sec?: number;   // how long the script takes to say at `wpm`
  slides: { slide_index: number; seconds: number; text: string }[];
}

// Understanding of the deck (backend deck_insights.py)
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

export interface BackendHealth {
  status: string;
  binaries: Record<string, boolean>;
  local_ml: Record<string, boolean>;
  // Where the partner / plans / feedback go: "custom" = LLM_BASE_URL (e.g. Gemini's OpenAI endpoint)
  llm: { provider: "openai" | "custom" | null; base_url: string | null; model: string | null };
  tts: { base_url: string | null; voice: string | null };
  providers: { openai: boolean };
}
