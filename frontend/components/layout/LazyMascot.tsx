"use client";

// Mate, loaded once the page is idle: its avatar library (~160 KB) stays out of every page's
// first download, and nothing on the page waits for it.

import dynamic from "next/dynamic";
import { useIdle } from "@/hooks/useIdle";

const Mascot = dynamic(() => import("./Mascot"), { ssr: false });

export default function LazyMascot() {
  return useIdle(3000) ? <Mascot /> : null;
}
