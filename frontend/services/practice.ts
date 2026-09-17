import { api } from "./api";
import type { PracticeSession, SessionType } from "@/types";

export const practiceService = {
  startSession: (session_type: SessionType) =>
    api.post<PracticeSession>("/practice/start", { session_type }),

  endSession: (session_id: string, duration: number) =>
    api.post<PracticeSession>("/practice/end", { session_id, duration }),

  getHistory: () => api.get<PracticeSession[]>("/practice/history"),
};
