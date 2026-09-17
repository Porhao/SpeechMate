"use client";

import { useEffect, useRef, useCallback } from "react";
import { WS_BASE_URL } from "@/constants";
import { useFeedbackStore } from "@/store/useFeedbackStore";

export function useWebSocket(sessionId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const { updateLiveFeedback, appendTranscript } = useFeedbackStore();

  const connect = useCallback(() => {
    if (!sessionId) return;
    const token = localStorage.getItem("access_token");
    ws.current = new WebSocket(`${WS_BASE_URL}/session/${sessionId}?token=${token}`);

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data as string);
      switch (msg.type) {
        case "speech.transcript":
          appendTranscript(msg.data);
          break;
        case "speech.fluency":
          updateLiveFeedback({ fluency: msg.data });
          break;
        case "speech.pronunciation":
          updateLiveFeedback({ pronunciation: msg.data });
          break;
        case "vision.eyecontact":
          updateLiveFeedback({ eye_contact: msg.data });
          break;
        case "vision.confidence":
          updateLiveFeedback({ confidence: msg.data });
          break;
      }
    };

    ws.current.onclose = () => {
      setTimeout(connect, 3000);
    };
  }, [sessionId, appendTranscript, updateLiveFeedback]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);

  const send = useCallback((type: string, data: unknown) => {
    ws.current?.send(JSON.stringify({ type, data }));
  }, []);

  return { send };
}
