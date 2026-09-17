export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export const SESSION_TYPES = ["Conversation", "Interview", "Presentation", "Pronunciation"] as const;

export const SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"] as const;

export const COMMUNICATION_GOALS = [
  "Improve Fluency",
  "Improve Pronunciation",
  "Reduce Anxiety",
  "Improve Presentations",
] as const;

export const SPEAKING_CHALLENGES = [
  "Stuttering",
  "Pronunciation",
  "Speaking Pace",
  "Confidence",
  "Eye Contact",
] as const;

export const PRACTICE_TYPES = [
  "Conversation",
  "Presentation",
  "Interview",
  "Storytelling",
] as const;

export const COLORS = {
  primary: "#2563EB",
  secondary: "#7C3AED",
  success: "#22C55E",
  warning: "#F59E0B",
  error: "#EF4444",
  textPrimary: "#0F172A",
  textSecondary: "#64748B",
  border: "#E2E8F0",
} as const;

export const METRIC_LABELS: Record<string, string> = {
  fluency_score: "Fluency",
  pronunciation_score: "Pronunciation",
  eye_contact_score: "Eye Contact",
  confidence_score: "Confidence",
  posture_score: "Posture",
  speaking_rate: "Speaking Pace",
};
