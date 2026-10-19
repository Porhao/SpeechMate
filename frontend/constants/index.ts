export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export const SKILL_LEVELS = ["Beginner", "Intermediate", "Advanced"] as const;

export const PRACTICE_TYPES = [
  "Conversation",
  "Presentation",
  "Interview",
  "Storytelling",
] as const;
