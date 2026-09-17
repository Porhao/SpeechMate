import { api } from "./api";
import type { FullAnalysisResult } from "@/types";

export const analysisService = {
  run: (sessionId: string) =>
    api.post<FullAnalysisResult>("/analysis/run", { session_id: sessionId }),
};
