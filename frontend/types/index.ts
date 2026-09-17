export interface User {
  id: string;
  full_name: string;
  email: string;
  role: string;
  language: string;
  created_at: string;
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

export interface PracticeSession {
  id: string;
  user_id: string;
  session_type: SessionType;
  duration: number;
  created_at: string;
}

export interface SpeechAnalysis {
  id: string;
  session_id: string;
  fluency_score: number;
  pronunciation_score: number;
  speaking_rate: number;
  filler_word_count: number;
  stuttering_score: number;
}

export interface VisionAnalysis {
  id: string;
  session_id: string;
  eye_contact_score: number;
  confidence_score: number;
  posture_score: number;
  emotion_label: string;
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
  user_id: string;
  metric_name: string;
  metric_value: number;
  recorded_at: string;
}

export interface Report {
  id: string;
  user_id: string;
  report_url: string;
  report_type: string;
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

// Response shape of POST /analysis/run — the full multimodal pipeline result
export interface FullAnalysisResult {
  session_id: string;
  transcript: string;
  language: {
    primary_language: string;
    is_code_switching: boolean;
    accent_type: string;
    english_ratio: number;
    malay_ratio: number;
    // Every flagged pronunciation deviation, pre-sorted into whether it's
    // consistent Malaysian-English phonology (not an error) or something
    // that would actually cost the speaker intelligibility. This is the
    // accent-fair distinction — regional variation is never blended into
    // the same "wrong" bucket as an error that would trip up a listener.
    pronunciation_flags?: {
      word: string;
      category: "regional" | "intelligibility";
      note: string;
    }[];
  };
  speech: {
    fluency_score: number;
    speaking_rate: number;
    pronunciation_score: number;
    stuttering_score: number;
    stuttering_severity: string;
    filler_count: number;
    filler_per_minute: number;
    top_filler: string;
    pause_frequency: number;
    fluency_grade: string;
  };
  vision: {
    eye_contact_score: number;
    posture_score: number;
    dominant_emotion: string;
    confidence_score: number;
    confidence_label: string;
  };
  communication_score: {
    overall_score: number;
    grade: string;
    strengths: string[];
    improvement_areas: string[];
  };
  recommendations: {
    weekly_focus: string;
    daily_target_minutes: number;
    tips: string[];
    progress_forecast: string;
    exercises: {
      title: string;
      description: string;
      practice_type: string;
      daily_minutes: number;
      priority: string;
      metric_target: string;
    }[];
  };
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
