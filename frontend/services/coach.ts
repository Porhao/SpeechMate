import { api } from "./api";
import type { ChatMessage } from "@/types";

export const coachService = {
  chat: (question: string, history: ChatMessage[]) =>
    api.post<{ answer: string }>("/coach/chat", { question, history }),
};
